import json
import logging
import os

from aws_lambda_powertools import Tracer

from common.const import PERMISSION_USER_ALL
from common.ddb_service.client import DynamoDbUtilsService
from common.response import no_content
from create_user import _check_action_permission
from libs.data_types import PARTITION_KEYS
from libs.utils import permissions_check, response_error

tracer = Tracer()
user_table = os.environ.get('MULTI_USER_TABLE')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)


@tracer.capture_lambda_handler
def handler(event, ctx):
    try:
        logger.info(json.dumps(event))
        body = json.loads(event['body'])
        user_name_list = body['user_name_list']

        requestor_name = permissions_check(event, [PERMISSION_USER_ALL])

        for username in user_name_list:
            check_permission_resp = _check_action_permission(requestor_name, username)
            if check_permission_resp:
                return check_permission_resp

            # todo: need to figure out what happens to user's resources: models, inferences, trainings and so on
            ddb_service.delete_item(user_table, keys={
                'kind': PARTITION_KEYS.user,
                'sort_key': username
            })

        return no_content(message='Users Deleted')
    except Exception as e:
        return response_error(e)
