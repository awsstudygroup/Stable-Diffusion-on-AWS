import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from aws_lambda_powertools import Tracer

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok
from libs.comfy_data_types import ComfySyncTable
from libs.utils import response_error

tracer = Tracer()
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

region = os.environ.get('AWS_REGION')
bucket_name = os.environ.get('S3_BUCKET_NAME')
inference_monitor_table = os.environ.get('INSTANCE_MONITOR_TABLE')
sync_table = os.environ.get('SYNC_TABLE')
endpoint_table = os.environ.get('ENDPOINT_TABLE')
config_table = os.environ.get('CONFIG_TABLE')

ddb_service = DynamoDbUtilsService(logger=logger)


@dataclass
class PrepareEnvEvent:
    prepare_id: Optional[str]
    endpoint_name: str
    need_reboot: bool = False
    prepare_type: Optional[str] = 'default'
    # notice !!! must not be prefixed with "/"
    s3_source_path: Optional[str] = ''
    local_target_path: Optional[str] = ''
    sync_script: Optional[str] = ''


def get_endpoint_info(endpoint_name: str):
    endpoint_raw = ddb_service.scan(endpoint_table, filters={'endpoint_name': endpoint_name})[0] if ddb_service.scan(endpoint_table, filters={'endpoint_name': endpoint_name}) else None
    logger.debug(f'endpoint_raw is : {endpoint_raw}')
    if not endpoint_raw:
        raise Exception(f'sagemaker endpoint with name {endpoint_name} is not found')

    endpoint_info = ddb_service.deserialize(endpoint_raw)
    logger.debug(f'endpoint_info is : {endpoint_info}')

    if endpoint_info is None or len(endpoint_info) == 0:
        raise Exception(f'sagemaker endpoint with name {endpoint_name} is not found')

    if endpoint_info['endpoint_status'] != 'InService':
        raise Exception(f'sagemaker endpoint is not ready with status: {endpoint_info["endpoint_status"]}')
    return endpoint_info


def prepare_sagemaker_env(request_id: str, event: PrepareEnvEvent):
    endpoint_name = event.endpoint_name
    if endpoint_name is None:
        raise Exception(f'endpoint name should not be null')
    endpoint_info = get_endpoint_info(endpoint_name)
    if not endpoint_info:
        raise Exception(f'endpoint not found with name {endpoint_name}')

    sync_job = ComfySyncTable(
        request_id=request_id if event.prepare_id is None else event.prepare_id,
        endpoint_name=event.endpoint_name,
        endpoint_id=endpoint_info['EndpointDeploymentJobId'],
        instance_count=endpoint_info['current_instance_count'],
        prepare_type=event.prepare_type,
        need_reboot=event.need_reboot,
        s3_source_path=event.s3_source_path,
        local_target_path=event.local_target_path,
        sync_script=event.sync_script,
        endpoint_snapshot=endpoint_info,
        request_time=int(datetime.now().timestamp()),
        request_time_str=datetime.now().isoformat(),
    )
    save_sync_ddb_resp = ddb_service.put_items(sync_table, entries=sync_job.__dict__)
    logger.info(str(save_sync_ddb_resp))


@tracer.capture_lambda_handler
def handler(raw_event, ctx):
    try:
        logger.info(f"prepare env start... Received event: {raw_event}")
        logger.info(f"Received ctx: {ctx}")
        request_id = ctx.aws_request_id

        event = PrepareEnvEvent(**json.loads(raw_event['body']))
        prepare_sagemaker_env(request_id, event)
        return ok(data=event.endpoint_name)
    except Exception as e:
        return response_error(e)
