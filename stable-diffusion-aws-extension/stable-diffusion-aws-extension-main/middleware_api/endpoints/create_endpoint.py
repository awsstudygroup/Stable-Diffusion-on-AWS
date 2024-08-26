import json
import logging
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import boto3
from aws_lambda_powertools import Tracer

from common.const import PERMISSION_ENDPOINT_ALL, PERMISSION_ENDPOINT_CREATE
from common.ddb_service.client import DynamoDbUtilsService
from common.excepts import BadRequestException
from common.response import bad_request, accepted
from common.util import resolve_instance_invocations_num
from libs.data_types import Endpoint, Workflow
from libs.enums import EndpointStatus, EndpointType
from libs.utils import response_error, permissions_check, get_workflow_by_name

tracer = Tracer()
sagemaker_endpoint_table = os.environ.get('ENDPOINT_TABLE_NAME')
aws_region = os.environ.get('AWS_REGION')
s3_bucket_name = os.environ.get('S3_BUCKET_NAME')
async_success_topic = os.environ.get('SNS_INFERENCE_SUCCESS')
async_error_topic = os.environ.get('SNS_INFERENCE_ERROR')

queue_url = os.environ.get('COMFY_QUEUE_URL')
sync_table = os.environ.get('COMFY_SYNC_TABLE')
instance_monitor_table = os.environ.get('COMFY_INSTANCE_MONITOR_TABLE')
esd_version = os.environ.get("ESD_VERSION")
esd_commit_id = os.environ.get("ESD_COMMIT_ID")

account_id = os.environ.get("ACCOUNT_ID")
region = os.environ.get("AWS_REGION")
url_suffix = os.environ.get("URL_SUFFIX")

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

sagemaker = boto3.client('sagemaker')
ddb_service = DynamoDbUtilsService(logger=logger)


@dataclass
class CreateEndpointEvent:
    instance_type: str
    autoscaling_enabled: bool
    assign_to_roles: [str]
    initial_instance_count: str
    max_instance_number: str = "1"
    min_instance_number: str = "0"
    endpoint_name: str = None
    # real-time / async
    endpoint_type: str = None
    custom_docker_image_uri: str = None
    custom_extensions: str = ""
    # service for: sd / comfy
    service_type: str = "sd"
    workflow: Optional[Workflow] = None
    workflow_name: str = ""
    # todo will be removed
    creator: str = ""


def check_custom_extensions(event: CreateEndpointEvent):
    if event.custom_extensions:
        logger.info(f"custom_extensions: {event.custom_extensions}")
        extensions_array = re.split('[ ,\n]+', event.custom_extensions)
        extensions_array = list(set(extensions_array))
        extensions_array = list(filter(None, extensions_array))

        for extension in extensions_array:
            pattern = r'^https://github\.com/[^#/]+/[^#/]+\.git#[^#]+#[a-fA-F0-9]{40}$'
            if not re.match(pattern, extension):
                raise BadRequestException(
                    message=f"extension format is invalid: {extension}, valid format is like "
                            f"https://github.com/awslabs/stable-diffusion-aws-extension.git#main#"
                            f"a096556799b7b0686e19ec94c0dbf2ca74d8ffbc")

        # make extensions_array to string again
        event.custom_extensions = ','.join(extensions_array)

        logger.info(f"formatted custom_extensions: {event.custom_extensions}")

        if len(extensions_array) >= 3:
            raise BadRequestException(message="custom_extensions should be at most 3")

    return event


def get_docker_image_uri(event: CreateEndpointEvent):
    # if it has custom extensions, then start from file image
    if event.custom_docker_image_uri:
        return event.custom_docker_image_uri

    return f"{account_id}.dkr.ecr.{region}.{url_suffix}/esd-inference:{esd_version}"


def create_from_workflow(event: CreateEndpointEvent):
    if event.workflow_name:
        event.workflow = get_workflow_by_name(event.workflow_name)
        if event.workflow.status != 'Enabled':
            raise BadRequestException(f"{event.workflow_name} is {event.workflow.status}")

    return event


# POST /endpoints
@tracer.capture_lambda_handler
def handler(raw_event, ctx):
    try:
        logger.info(json.dumps(raw_event))
        event = CreateEndpointEvent(**json.loads(raw_event['body']))

        permissions_check(raw_event, [PERMISSION_ENDPOINT_ALL, PERMISSION_ENDPOINT_CREATE])

        if event.endpoint_type not in EndpointType.List.value:
            raise BadRequestException(message=f"{event.endpoint_type} endpoint is not supported yet")

        if int(event.initial_instance_count) < 1:
            raise BadRequestException(f"initial_instance_count should be at least 1: {event.endpoint_name}")

        if event.autoscaling_enabled:
            if event.endpoint_type == EndpointType.RealTime.value and int(event.min_instance_number) < 1:
                raise BadRequestException(
                    f"min_instance_number should be at least 1 for real-time endpoint: {event.endpoint_name}")

            if event.endpoint_type == EndpointType.Async.value and int(event.min_instance_number) < 0:
                raise BadRequestException(
                    f"min_instance_number should be at least 0 for async endpoint: {event.endpoint_name}")

        event = create_from_workflow(event)

        event = check_custom_extensions(event)

        endpoint_id = str(uuid.uuid4())
        short_id = endpoint_id[:7]
        endpoint_type = event.endpoint_type.lower()

        if event.endpoint_name:
            short_id = event.endpoint_name

        if event.workflow:
            if endpoint_type != 'async':
                raise BadRequestException(message=f"Your can't create Async endpoint only for workflow currently")
            short_id = event.workflow.name

        endpoint_name = f"{event.service_type}-{endpoint_type}-{short_id}"
        model_name = f"{endpoint_name}"
        endpoint_config_name = f"{endpoint_name}"

        model_data_url = f"s3://{s3_bucket_name}/data/model.tar.gz"

        s3_output_path = f"s3://{s3_bucket_name}/sagemaker_output/"

        initial_instance_count = int(event.initial_instance_count) if event.initial_instance_count else 1
        instance_type = event.instance_type

        endpoint_rows = ddb_service.scan(sagemaker_endpoint_table, filters=None)
        for endpoint_row in endpoint_rows:
            logger.info("endpoint_row:")
            logger.info(endpoint_row)
            endpoint = Endpoint(**(ddb_service.deserialize(endpoint_row)))
            logger.info("endpoint:")
            logger.info(endpoint.__dict__)

            if not endpoint.owner_group_or_role:
                continue

            # Compatible with fields used in older data, endpoint.status must be 'deleted'
            if endpoint.endpoint_status != EndpointStatus.DELETED.value and endpoint.status != 'deleted':
                for role in event.assign_to_roles:
                    if role in endpoint.owner_group_or_role:
                        return bad_request(
                            message=f"role [{role}] has a valid endpoint already, not allow to have another one")

        _create_sagemaker_model(model_name, model_data_url, endpoint_name, endpoint_id, event)

        try:
            if event.endpoint_type == EndpointType.RealTime.value:
                _create_endpoint_config_provisioned(endpoint_config_name, model_name,
                                                    initial_instance_count, instance_type)
            elif event.endpoint_type == EndpointType.Async.value:
                _create_endpoint_config_async(endpoint_config_name, s3_output_path, model_name,
                                              initial_instance_count, instance_type, event)
        except Exception as e:
            logger.error(f"error creating endpoint config with exception: {e}")
            sagemaker.delete_model(ModelName=model_name)
            return bad_request(message=str(e))

        try:
            response = sagemaker.create_endpoint(
                EndpointName=endpoint_name,
                EndpointConfigName=endpoint_config_name
            )
            logger.info(f"Successfully created endpoint: {response}")
        except Exception as e:
            logger.error(f"error creating endpoint with exception: {e}")
            sagemaker.delete_endpoint_config(EndpointConfigName=endpoint_config_name)
            sagemaker.delete_model(ModelName=model_name)
            return bad_request(message=str(e))

        data = Endpoint(
            EndpointDeploymentJobId=endpoint_id,
            endpoint_name=endpoint_name,
            startTime=datetime.now().isoformat(),
            endpoint_status=EndpointStatus.CREATING.value,
            autoscaling=event.autoscaling_enabled,
            owner_group_or_role=event.assign_to_roles,
            current_instance_count="0",
            instance_type=instance_type,
            endpoint_type=event.endpoint_type,
            min_instance_number=event.min_instance_number,
            max_instance_number=event.max_instance_number,
            custom_extensions=event.custom_extensions,
            service_type=event.service_type,
        ).__dict__

        ddb_service.put_items(table=sagemaker_endpoint_table, entries=data)
        logger.info(f"Successfully created endpoint deployment: {data}")

        return accepted(
            message=f"Endpoint deployment started: {endpoint_name}",
            data=data
        )
    except Exception as e:
        return response_error(e)


@tracer.capture_method
def _create_sagemaker_model(name, model_data_url, endpoint_name, endpoint_id, event: CreateEndpointEvent):
    tracer.put_annotation('endpoint_name', endpoint_name)
    image_url = get_docker_image_uri(event)

    if event.workflow:
        image_url = event.workflow.image_uri

    environment = {
        'LOG_LEVEL': os.environ.get('LOG_LEVEL') or logging.ERROR,
        'S3_BUCKET_NAME': s3_bucket_name,
        'IMAGE_URL': image_url,
        'INSTANCE_TYPE': event.instance_type,
        'ENDPOINT_NAME': endpoint_name,
        'ENDPOINT_ID': endpoint_id,
        'EXTENSIONS': event.custom_extensions,
        'CREATED_AT': datetime.utcnow().isoformat(),
        'COMFY_QUEUE_URL': queue_url or '',
        'COMFY_SYNC_TABLE': sync_table or '',
        'COMFY_INSTANCE_MONITOR_TABLE': instance_monitor_table or '',
        'ESD_VERSION': esd_version,
        'ESD_COMMIT_ID': esd_commit_id,
        'SERVICE_TYPE': event.service_type,
        'ON_SAGEMAKER': 'true',
        'AWS_REGION': aws_region,
        'AWS_DEFAULT_REGION': aws_region,
    }

    if event.workflow:
        environment['WORKFLOW_NAME'] = event.workflow.name
        environment['APP_CWD'] = '/home/ubuntu/ComfyUI'

    primary_container = {
        'Image': image_url,
        'ModelDataUrl': model_data_url,
        'Environment': environment,
    }

    tracer.put_metadata('primary_container', primary_container)

    logger.info(f"Creating model resource PrimaryContainer: {primary_container}")

    response = sagemaker.create_model(
        ModelName=name,
        PrimaryContainer=primary_container,
        ExecutionRoleArn=os.environ.get("EXECUTION_ROLE_ARN"),
    )
    logger.info(f"Successfully created model resource: {response}")


def get_production_variants(model_name, instance_type, initial_instance_count):
    return [
        {
            'VariantName': 'prod',
            'ModelName': model_name,
            'InitialInstanceCount': initial_instance_count,
            'InstanceType': instance_type,
            "ModelDataDownloadTimeoutInSeconds": 60 * 20,  # Specify the model download timeout in seconds.
            "ContainerStartupHealthCheckTimeoutInSeconds": 60 * 60,  # Specify the health checkup timeout in seconds
        }
    ]


@tracer.capture_method
def _create_endpoint_config_provisioned(endpoint_config_name, model_name, initial_instance_count,
                                        instance_type):
    production_variants = get_production_variants(model_name, instance_type, initial_instance_count)

    logger.info(f"Creating endpoint configuration ProductionVariants: {production_variants}")

    response = sagemaker.create_endpoint_config(
        EndpointConfigName=endpoint_config_name,
        ProductionVariants=production_variants
    )
    logger.info(f"Successfully created endpoint configuration: {response}")


@tracer.capture_method
def _create_endpoint_config_async(endpoint_config_name, s3_output_path, model_name, initial_instance_count,
                                  instance_type, event: CreateEndpointEvent):
    if event.service_type != "sd":
        success_topic = os.environ.get('COMFY_SNS_INFERENCE_SUCCESS')
        error_topic = os.environ.get('COMFY_SNS_INFERENCE_ERROR')
    else:
        success_topic = async_success_topic
        error_topic = async_error_topic

    async_inference_config = {
        "OutputConfig": {
            "S3OutputPath": s3_output_path,
            "NotificationConfig": {
                "SuccessTopic": success_topic,
                "ErrorTopic": error_topic
            }
        },
        "ClientConfig": {
            "MaxConcurrentInvocationsPerInstance": resolve_instance_invocations_num(instance_type, event.service_type),
        }
    }

    production_variants = get_production_variants(model_name, instance_type, initial_instance_count)

    logger.info(f"Creating endpoint configuration AsyncInferenceConfig: {async_inference_config}")
    logger.info(f"Creating endpoint configuration ProductionVariants: {production_variants}")

    response = sagemaker.create_endpoint_config(
        EndpointConfigName=endpoint_config_name,
        AsyncInferenceConfig=async_inference_config,
        ProductionVariants=production_variants
    )
    logger.info(f"Successfully created endpoint configuration: {response}")
