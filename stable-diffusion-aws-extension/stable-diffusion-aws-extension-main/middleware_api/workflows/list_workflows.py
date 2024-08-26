import json
import logging
import os

import boto3
from aws_lambda_powertools import Tracer

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok
from common.util import get_query_param
from libs.data_types import Workflow
from libs.utils import response_error, decode_last_key, encode_last_key

tracer = Tracer()

workflows_table = os.environ.get('WORKFLOWS_TABLE')

ddb = boto3.resource('dynamodb')
table = ddb.Table(workflows_table)
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)


@tracer.capture_lambda_handler
def handler(event, ctx):
    _filter = {}

    try:
        logger.info(json.dumps(event))

        exclusive_start_key = get_query_param(event, 'exclusive_start_key')
        limit = int(get_query_param(event, 'limit', 10))

        scan_kwargs = {
            'Limit': limit,
        }

        if exclusive_start_key:
            scan_kwargs['ExclusiveStartKey'] = decode_last_key(exclusive_start_key)

        response = table.scan(**scan_kwargs)
        scan_rows = response.get('Items', [])
        last_evaluated_key = encode_last_key(response.get('LastEvaluatedKey'))

        results = []

        for row in scan_rows:
            logger.info(f"row: {row}")
            results.append(Workflow(**row).__dict__)

        results = sort_workflows(results)

        data = {
            'workflows': results,
            'last_evaluated_key': last_evaluated_key
        }

        return ok(data=data, decimal=True)
    except Exception as e:
        return response_error(e)


def sort_workflows(data):
    if len(data) == 0:
        return data

    return sorted(data, key=lambda x: x['create_time'], reverse=True)
