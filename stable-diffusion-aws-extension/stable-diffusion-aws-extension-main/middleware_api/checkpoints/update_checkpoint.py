import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict

import boto3
from aws_lambda_powertools import Tracer

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, not_found, bad_request, accepted
from create_checkpoint import check_ckpt_name_unique
from libs.common_tools import complete_multipart_upload
from libs.data_types import CheckPoint, CheckPointStatus
from libs.utils import response_error

tracer = Tracer()
checkpoint_table = os.environ.get('CHECKPOINT_TABLE')
rename_lambda_name = os.environ.get('RENAME_LAMBDA_NAME')
bucket_name = os.environ.get('S3_BUCKET_NAME')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)
lambda_client = boto3.client('lambda')


@dataclass
class UpdateCheckPointEvent:
    name: str = None
    status: str = None
    multi_parts_tags: Dict[str, Any] = None


# PUT /checkpoints/{id}
@tracer.capture_lambda_handler
def handler(raw_event, context):
    try:
        logger.info(f'event: {raw_event}')
        # todo will be removed
        # permissions_check(raw_event, [PERMISSION_CHECKPOINT_ALL])

        event = UpdateCheckPointEvent(**json.loads(raw_event['body']))

        checkpoint_id = raw_event['pathParameters']['id']
        raw_checkpoint = ddb_service.get_item(table=checkpoint_table, key_values={
            'id': checkpoint_id
        })
        if raw_checkpoint is None or len(raw_checkpoint) == 0:
            return not_found(
                message=f'checkpoint not found with id {checkpoint_id}'
            )

        checkpoint = CheckPoint(**raw_checkpoint)
        if event.status:
            return update_status(event, checkpoint)
        if event.name:
            return update_name(event, checkpoint)
        return ok()
    except Exception as e:
        return response_error(e)


@tracer.capture_method
def update_status(event: UpdateCheckPointEvent, checkpoint: CheckPoint):
    if event.multi_parts_tags is None or len(event.multi_parts_tags) == 0:
        return bad_request(message='multi parts tags is empty')
    new_status = CheckPointStatus[event.status]
    complete_multipart_upload(checkpoint, event.multi_parts_tags)
    # if complete part failed, then no update
    ddb_service.update_item(
        table=checkpoint_table,
        key={
            'id': checkpoint.id,
        },
        field_name='checkpoint_status',
        value=new_status
    )
    data = {
        'checkpoint': {
            'id': checkpoint.id,
            'type': checkpoint.checkpoint_type,
            's3_location': checkpoint.s3_location,
            'status': checkpoint.checkpoint_status.value,
            'params': checkpoint.params
        }
    }
    return ok(data=data)


@tracer.capture_method
def update_name(event: UpdateCheckPointEvent, checkpoint: CheckPoint):
    if checkpoint.checkpoint_status != CheckPointStatus.Active:
        return bad_request(message='only active can update name')

    old_name = checkpoint.checkpoint_names[0]
    new_name = event.name

    if old_name == new_name:
        return ok(message='no need to update')

    check_ckpt_name_unique([event.name])

    s3_path = checkpoint.s3_location.replace(f's3://{bucket_name}/', '')

    lambda_client.invoke(
        FunctionName=rename_lambda_name,
        InvocationType='Event',
        Payload=json.dumps({
            'id': checkpoint.id,
            's3_path': s3_path,
            'old_name': old_name,
            'new_name': new_name,
        })
    )

    return accepted(message='rename is processing, please wait')
