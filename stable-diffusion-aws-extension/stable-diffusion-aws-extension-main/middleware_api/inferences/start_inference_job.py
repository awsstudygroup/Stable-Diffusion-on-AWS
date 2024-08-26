import json
import logging
import os
from datetime import datetime

from aws_lambda_powertools import Tracer
from sagemaker import Predictor
from sagemaker.deserializers import JSONDeserializer
from sagemaker.predictor_async import AsyncPredictor
from sagemaker.serializers import JSONSerializer

from common.const import PERMISSION_INFERENCE_ALL
from common.ddb_service.client import DynamoDbUtilsService
from common.excepts import BadRequestException
from common.response import accepted
from common.util import record_latency_metrics, record_count_metrics
from get_inference_job import get_infer_data
from inference_libs import parse_sagemaker_result, update_inference_job_table
from libs.data_types import InferenceJob, InvocationRequest
from libs.enums import EndpointType
from libs.utils import response_error, permissions_check, log_json

tracer = Tracer()
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

inference_table_name = os.environ.get('INFERENCE_JOB_TABLE')

ddb_service = DynamoDbUtilsService(logger=logger)

predictors = {}


@tracer.capture_lambda_handler
def handler(event: dict, _):
    try:
        logger.info(json.dumps(event))
        _filter = {}

        inference_id = event['pathParameters']['id']

        if not inference_id:
            raise BadRequestException("InferenceJobId is required")

        username = permissions_check(event, [PERMISSION_INFERENCE_ALL])

        # get the inference job from ddb by job id
        inference_raw = ddb_service.get_item(inference_table_name, {
            'InferenceJobId': inference_id
        })

        if inference_raw is None or len(inference_raw) == 0:
            raise BadRequestException(f"InferenceJobId {inference_id} not found")

        job = InferenceJob(**inference_raw)

        return inference_start(job, username)

    except Exception as e:
        return response_error(e)


@tracer.capture_method
def inference_start(job: InferenceJob, username):
    endpoint_name = job.params['sagemaker_inference_endpoint_name']
    models = {}
    if 'used_models' in job.params:
        models = {
            "space_free_size": 4e10,
            **job.params['used_models'],
        }

    payload = InvocationRequest(
        id=job.InferenceJobId,
        task=job.taskType,
        workflow=job.workflow,
        username=username,
        models=models,
        param_s3=job.params['input_body_s3'],
        payload_string=job.payload_string
    )

    log_json("inference job", job.__dict__)
    log_json("inference invoke payload", payload.__dict__)

    if job.inference_type == EndpointType.RealTime.value:
        update_inference_job_table(job.InferenceJobId, 'startTime', datetime.now().isoformat())
        return real_time_inference(payload, job, endpoint_name)

    return async_inference(payload, job, endpoint_name)


@tracer.capture_method
def real_time_inference(payload: InvocationRequest, job: InferenceJob, ep_name: str):
    tracer.put_annotation(key="InferenceJobId", value=job.InferenceJobId)
    sagemaker_out = predictor_real_time_predict(endpoint_name=ep_name,
                                                data=payload.__dict__,
                                                inference_id=job.InferenceJobId,
                                                )

    if 'error' in sagemaker_out:
        record_count_metrics(ep_name=ep_name,
                             metric_name='InferenceFailed',
                             workflow=job.workflow,
                             )
        update_inference_job_table(job.InferenceJobId, 'sagemakerRaw', str(sagemaker_out))
        raise Exception(str(sagemaker_out))

    parse_sagemaker_result(sagemaker_out, job.createTime, job.InferenceJobId, job.taskType, ep_name)

    record_count_metrics(ep_name=ep_name,
                         metric_name='InferenceSucceed',
                         workflow=job.workflow,
                         )
    record_latency_metrics(start_time=sagemaker_out['start_time'],
                           ep_name=ep_name,
                           metric_name='InferenceLatency',
                           workflow=job.workflow,
                           )

    return get_infer_data(job.InferenceJobId)


@tracer.capture_method
def get_real_time_predict_client(endpoint_name):
    tracer.put_annotation(key="endpoint_name", value=endpoint_name)
    if endpoint_name in predictors:
        return predictors[endpoint_name]

    predictor = Predictor(endpoint_name)
    predictor.serializer = JSONSerializer()
    predictor.deserializer = JSONDeserializer()

    predictors[endpoint_name] = predictor

    return predictor


@tracer.capture_method
def get_async_predict_client(endpoint_name):
    tracer.put_annotation(key="endpoint_name", value=endpoint_name)
    if endpoint_name in predictors:
        return predictors[endpoint_name]

    predictor = Predictor(endpoint_name)
    predictor = AsyncPredictor(predictor, name=endpoint_name)
    predictor.serializer = JSONSerializer()
    predictor.deserializer = JSONDeserializer()

    predictors[endpoint_name] = predictor

    return predictor


@tracer.capture_method
def predictor_real_time_predict(endpoint_name, data, inference_id):
    return get_real_time_predict_client(endpoint_name).predict(data=data, inference_id=inference_id)


@tracer.capture_method
def predictor_async_predict(endpoint_name, data, inference_id):
    tracer.put_annotation(key="inference_id", value=inference_id)
    initial_args = {"InvocationTimeoutSeconds": 3600}
    return get_async_predict_client(endpoint_name).predict_async(data=data,
                                                                 initial_args=initial_args,
                                                                 inference_id=inference_id)


@tracer.capture_method
def async_inference(payload: InvocationRequest, job: InferenceJob, endpoint_name):
    tracer.put_annotation(key="inference_id", value=job.InferenceJobId)

    prediction = predictor_async_predict(endpoint_name=endpoint_name,
                                         data=payload.__dict__,
                                         inference_id=job.InferenceJobId)
    logger.info(f"prediction: {prediction}")
    output_path = prediction.output_path

    # update the ddb job status to 'inprogress' and save to ddb
    job.status = 'inprogress'
    job.params['output_path'] = output_path
    ddb_service.put_items(inference_table_name, job.__dict__)

    data = {
        'InferenceJobId': job.InferenceJobId,
        'status': job.status,

        # todo inference will remove in the next version
        'inference': {
            'inference_id': job.InferenceJobId,
            'status': job.status,
            'endpoint_name': endpoint_name,
            'output_path': output_path
        }
    }

    return accepted(data=data)
