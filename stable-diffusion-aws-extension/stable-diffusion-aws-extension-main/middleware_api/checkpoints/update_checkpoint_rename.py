import logging
import os

import boto3
from aws_lambda_powertools import Tracer

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok
from libs.utils import response_error

tracer = Tracer()
checkpoint_table = os.environ.get('CHECKPOINT_TABLE')
bucket_name = os.environ.get('S3_BUCKET_NAME')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)
s3_client = boto3.client('s3')


@tracer.capture_lambda_handler
def handler(raw_event, context):
    logger.info(f'event: {raw_event}')

    try:
        ckpt_id = raw_event['id']
        s3_path = raw_event['s3_path']
        old_name = raw_event['old_name']
        new_name = raw_event['new_name']

        rename_s3_object(f"{s3_path}/{old_name}", f"{s3_path}/{new_name}")

        ddb_service.update_item(
            table=checkpoint_table,
            key={
                'id': ckpt_id,
            },
            field_name='checkpoint_names',
            value=[
                new_name
            ]
        )

        return ok(message='update name success')
    except Exception as e:
        return response_error(e)


@tracer.capture_method
def rename_s3_object(old_key, new_key):
    # Copy the object to the new key
    s3_client.copy_object(Bucket=bucket_name, CopySource={'Bucket': bucket_name, 'Key': old_key}, Key=new_key)

    # Delete the original object
    s3_client.delete_object(Bucket=bucket_name, Key=old_key)
