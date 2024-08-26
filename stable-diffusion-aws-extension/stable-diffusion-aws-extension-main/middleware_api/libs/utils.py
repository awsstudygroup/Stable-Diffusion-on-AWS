import base64
import json
import logging
import os

import boto3
from aws_lambda_powertools import Tracer
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from common.ddb_service.client import DynamoDbUtilsService
from common.excepts import ForbiddenException, UnauthorizedException, NotFoundException, BadRequestException
from common.response import unauthorized, forbidden, not_found, bad_request
from libs.data_types import PARTITION_KEYS, User, Role, Endpoint, Workflow

tracer = Tracer()
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

user_table = os.environ.get('MULTI_USER_TABLE')
s3_bucket_name = os.environ.get('S3_BUCKET_NAME')
ddb_service = DynamoDbUtilsService(logger=logger)

encode_type = "utf-8"
s3 = boto3.client('s3')
ddb = boto3.resource('dynamodb')
endpoint_table = ddb.Table(os.environ.get('ENDPOINT_TABLE_NAME'))
dynamodb = boto3.client('dynamodb')


@tracer.capture_method
def check_file_exists(key):
    try:
        s3.head_object(Bucket=s3_bucket_name, Key=key)
        return True
    except Exception as e:
        logger.error(e, exc_info=True)
        if e.response['Error']['Code'] == '404':
            return False
        else:
            raise e


@tracer.capture_method
def update_table_by_pk(table: str, pk_name: str, pk_value: str, key: str, value):
    logger.info(f"Update {table} with {pk_name}: {id}, key: {key}, value: {value}")
    try:
        ddb_client = boto3.resource('dynamodb')
        ddb_table = ddb_client.Table(table)
        ddb_table.update_item(
            Key={
                pk_name: pk_value,
            },
            UpdateExpression=f"set #k = :v",
            ExpressionAttributeNames={'#pk_name': pk_name, '#k': key},
            ExpressionAttributeValues={':v': value},
            ConditionExpression=f"attribute_exists(#pk_name)",
            ReturnValues="UPDATED_NEW"
        )
    except Exception as e:
        logger.error(f"Update {table} error: {e}")
        raise e


def get_endpoint_name_by_workflow_name(name: str, endpoint_type: str = 'async'):
    return f"comfy-{endpoint_type}-{name}"


@tracer.capture_method
def get_workflow_by_name(workflow_name: str):
    tracer.put_annotation(key="workflow_name", value=workflow_name)

    table_name = os.environ.get('WORKFLOWS_TABLE')

    response = dynamodb.get_item(
        TableName=table_name,
        Key={
            'name': {'S': workflow_name}
        }
    )
    logger.info(response)

    tracer.put_metadata(key="workflow_name", value=response)

    item = response.get('Item', None)

    if item is None:
        raise NotFoundException(f'workflow {workflow_name} not found')

    return Workflow(
        name=item['name']['S'],
        status=item['status']['S'],
        s3_location=item['s3_location']['S'],
        image_uri=item['image_uri']['S'],
        payload_json=item['payload_json']['S'],
        create_time=item['create_time']['S'],
    )


@tracer.capture_method
def get_endpoint_by_name(endpoint_name: str):
    tracer.put_annotation(key="endpoint_name", value=endpoint_name)

    scan_kwargs = {
        'IndexName': "endpoint_name-startTime-index",
        'KeyConditionExpression': Key('endpoint_name').eq(endpoint_name),
    }

    logger.info(scan_kwargs)

    response = endpoint_table.query(**scan_kwargs)

    tracer.put_metadata(key="endpoint_name", value=response)

    items = response.get('Items', [])

    if len(items) == 0:
        raise NotFoundException(f'endpoint with name {endpoint_name} not found')

    return Endpoint(**items[0])


def log_json(title, payload: any = None):
    logger.info(f"{title}: ")
    if payload:
        logger.info(json.dumps(payload, default=str))


class KeyEncryptService:

    def __init__(self, logging_level=logging.INFO):
        self.kms_client = boto3.client('kms')
        self.logger = logging.getLogger('boto3')
        self.logger.setLevel(logging_level)

    def encrypt(self, key_id: str, text: str) -> bytes:
        """
        Encrypts text by using the specified key.

        :param key_id: The ARN or ID of the key to use for encryption.
        :param text: The text need to be encrypted
        :return: The encrypted version of the text.
        """
        try:
            cipher_text = self.kms_client.encrypt(
                KeyId=key_id, Plaintext=text.encode())['CiphertextBlob']
        except ClientError as err:
            self.logger.error(
                "Couldn't encrypt text. Here's why: %s", err.response['Error']['Message'])
        else:
            self.logger.debug(f"Your ciphertext is: {cipher_text}")
            return cipher_text

    def decrypt(self, key_id: str, cipher_text: bytes) -> bytes:
        """
        Decrypts text previously encrypted with a key.

        :param key_id: The ARN or ID of the key used to decrypt the data.
        :param cipher_text: The encrypted text to decrypt.
        """
        try:
            text = self.kms_client.decrypt(KeyId=key_id, CiphertextBlob=cipher_text)['Plaintext']
        except ClientError as err:
            self.logger.error("Couldn't decrypt your ciphertext. Here's why: %s",
                              err.response['Error']['Message'])

        else:
            self.logger.debug(f"Your plaintext is {text.decode()}")
            return text


@tracer.capture_method
def check_user_existence(ddb_service, user_table, username):
    creator = ddb_service.query_items(table=user_table, key_values={
        'kind': PARTITION_KEYS.user,
        'sort_key': username,
    })

    return not creator or len(creator) == 0


@tracer.capture_method
def get_user_by_username(ddb_service, user_table, username):
    user_raw = ddb_service.query_items(table=user_table, key_values={
        'kind': PARTITION_KEYS.user,
        'sort_key': username,
    })

    if not user_raw or len(user_raw) == 0:
        return None

    return User(**(ddb_service.deserialize(user_raw[0])))


@tracer.capture_method
def get_user_roles(ddb_service, user_table_name, username):
    tracer.put_annotation(key="username", value=username)
    user = ddb_service.query_items(table=user_table_name, key_values={
        'kind': PARTITION_KEYS.user,
        'sort_key': username,
    })
    if not user or len(user) == 0:
        raise Exception(f'user: "{username}" not exist')

    user = User(**ddb_service.deserialize(user[0]))
    return user.roles


def response_error(e):
    try:
        logger.error(e, exc_info=True)
        raise e
    except UnauthorizedException as e:
        return unauthorized(message=str(e))
    except ForbiddenException as e:
        return forbidden(message=str(e))
    except NotFoundException as e:
        return not_found(message=str(e))
    except Exception as e:
        return bad_request(message=str(e))


def get_user_name(event: any):
    if 'headers' not in event:
        raise BadRequestException('Not found headers in event')

    username = None

    if 'username' in event['headers']:
        username = event['headers']['username']
    elif 'Authorization' in event['headers']:
        # todo compatibility with 1.4.0, will be removed
        authorization = event['headers']['Authorization']
        if authorization:
            username = base64.b16decode(authorization.replace('Bearer ', '').encode(encode_type)).decode(
                encode_type)

    if not username:
        raise UnauthorizedException("Unauthorized")

    return username


@tracer.capture_method
def permissions_check(event: any, permissions: [str]):
    username = get_user_name(event)

    tracer.put_annotation(key="username", value=username)

    if not user_table:
        raise Exception("MULTI_USER_TABLE not set")

    user = ddb_service.query_items(table=user_table, key_values={
        'kind': PARTITION_KEYS.user,
        'sort_key': username,
    })

    if not user or len(user) == 0:
        raise UnauthorizedException("Unauthorized")

    user = User(**ddb_service.deserialize(user[0]))
    logger.info(f'user: {user}')

    roles = ddb_service.scan(table=user_table, filters={
        'kind': PARTITION_KEYS.role,
        'sort_key': user.roles,
    })

    for role_raw in roles:
        role = Role(**(ddb_service.deserialize(role_raw)))
        logger.info(f'role: {role}')
        for permission in permissions:
            if permission in role.permissions:
                return username

    raise ForbiddenException(f"User {username} has no permissions: {permissions}")


def check_user_permissions(checkpoint_owners: [str], user_roles: [str], user_name: str) -> bool:
    if not checkpoint_owners or user_name in checkpoint_owners or '*' in checkpoint_owners:
        return True

    for user_role in user_roles:
        if user_role in checkpoint_owners:
            return True

    return False


@tracer.capture_method
def get_permissions_by_username(ddb_service, user_table, username):
    creator_roles = get_user_roles(ddb_service, user_table, username)
    roles = ddb_service.scan(table=user_table, filters={
        'kind': PARTITION_KEYS.role,
        'sort_key': creator_roles,
    })
    permissions = {}
    for role_raw in roles:
        role = Role(**(ddb_service.deserialize(role_raw)))
        for permission in role.permissions:
            permission_parts = permission.split(':')
            resource = permission_parts[0]
            action = permission_parts[1]

            if resource not in permissions:
                permissions[resource] = set()

            permissions[resource].add(action)

    return permissions


def encode_last_key(last_evaluated_key):
    if not last_evaluated_key:
        return None
    return base64.b64encode(json.dumps(last_evaluated_key).encode(encode_type)).decode(encode_type)


def decode_last_key(last_evaluated_key):
    if not last_evaluated_key:
        return None
    return json.loads(base64.b64decode(last_evaluated_key.encode(encode_type)).decode(encode_type))
