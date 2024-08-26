import concurrent.futures
import datetime
import json
import logging
import os
import urllib.parse
from dataclasses import dataclass
from typing import Any, Optional

import requests
from aws_lambda_powertools import Tracer

from common.ddb_service.client import DynamoDbUtilsService
from common.response import bad_request, forbidden
from common.const import COMFY_TYPE
from libs.common_tools import get_base_checkpoint_s3_key, multipart_upload_from_url
from libs.data_types import CheckPoint, CheckPointStatus
from libs.utils import get_user_roles, get_permissions_by_username

tracer = Tracer()
checkpoint_table = os.environ.get('CHECKPOINT_TABLE')
bucket_name = os.environ.get('S3_BUCKET_NAME')
checkpoint_type = ["Stable-diffusion", "embeddings", "Lora", "hypernetworks", "ControlNet", "VAE"]
user_table = os.environ.get('MULTI_USER_TABLE')
CN_MODEL_EXTS = [".pt", ".pth", ".ckpt", ".safetensors", ".yaml"]

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)
MAX_WORKERS = 10


@tracer.capture_method
def download_and_upload_models(url: str, base_key: str, file_names: list, multipart_upload: dict,
                               cannot_download: list):
    logger.info(f"download_and_upload_models: {url}, {base_key}, {file_names}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        # Add more headers if needed
    }
    response = requests.get(url, headers=headers, allow_redirects=False, stream=True)
    logger.info( response.status_code)
    if response and response.status_code == 307:
        logger.info(f"response:{response}, statuscode:{response} headers:{response.headers}")
        if response.headers and 'Location' in response.headers:
            logger.info(f"response ok:{response.headers.get('Location')}")
            url = response.headers.get('Location')
    parsed_url = urllib.parse.urlparse(url)
    filename = os.path.basename(parsed_url.path)
    if os.path.splitext(filename)[1] not in CN_MODEL_EXTS:
        logger.info(f"download_and_upload_models file error url:{url}, parsed_url:{parsed_url} filename:{filename}")
        cannot_download.append(url)
        return
    logger.info(f"file name is :{filename}")
    file_names.append(filename)
    s3_key = f'{base_key}/{filename}'
    logger.info(f"upload s3 key is :{filename}")
    multipart_upload[filename] = multipart_upload_from_url(url, bucket_name, s3_key)


def concurrent_upload(file_url: str, base_key, file_names, multipart_upload):
    cannot_download = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(download_and_upload_models, file_url, base_key, file_names, multipart_upload,
                                   cannot_download)]

        for future in concurrent.futures.as_completed(futures):
            future.result()
    if cannot_download:
        return cannot_download
    return None


@dataclass
class CreateCheckPointByUrlEvent:
    checkpoint_type: str
    params: dict[str, Any]
    url: str
    source_path: Optional[str] = None
    target_path: Optional[str] = None


@tracer.capture_lambda_handler
def handler(raw_event, context):
    logger.info(json.dumps(raw_event))

    request_id = context.aws_request_id
    event = CreateCheckPointByUrlEvent(**raw_event)

    if event.checkpoint_type == COMFY_TYPE:
        if not event.source_path or not event.target_path:
            return bad_request(message='Please check your source_path or target_path of the checkpoints')
        # such as source_path :"comfy/{comfy_endpoint}/{prepare_version}/models/"  target_path:"models/checkpoints"
        base_key = event.source_path
    else:
        base_key = get_base_checkpoint_s3_key(event.checkpoint_type, 'custom', request_id)
    file_names = []
    logger.info(f"start to upload model:{event.url}")
    checkpoint_params = {}
    if event.params is not None and len(event.params) > 0:
        checkpoint_params = event.params
    checkpoint_params['created'] = str(datetime.datetime.now())
    checkpoint_params['multipart_upload'] = {}

    user_roles = ['*']
    creator_permissions = {}
    if 'creator' in event.params and event.params['creator']:
        user_roles = get_user_roles(ddb_service, user_table, event.params['creator'])
        creator_permissions = get_permissions_by_username(ddb_service, user_table, event.params['creator'])

    if 'checkpoint' not in creator_permissions or \
            ('all' not in creator_permissions['checkpoint'] and 'create' not in creator_permissions['checkpoint']):
        return forbidden(message=f"user has no permissions to create a model")

    cannot_download = concurrent_upload(event.url, base_key, file_names, checkpoint_params['multipart_upload'])
    if cannot_download:
        return bad_request(message=f"contains invalid urls:{cannot_download}")

    logger.info("finished upload, prepare to insert item to ddb")
    checkpoint = CheckPoint(
        id=request_id,
        checkpoint_type=event.checkpoint_type,
        s3_location=f's3://{bucket_name}/{base_key}',
        checkpoint_names=file_names,
        checkpoint_status=CheckPointStatus.Active,
        params=checkpoint_params,
        timestamp=datetime.datetime.now().timestamp(),
        allowed_roles_or_users=user_roles,
        source_path=event.source_path,
        target_path=event.target_path,
    )
    ddb_service.put_items(table=checkpoint_table, entries=checkpoint.__dict__)
    logger.info("finished insert item to ddb")
    data = {
        'checkpoint': {
            'id': request_id,
            'type': event.checkpoint_type,
            's3_location': checkpoint.s3_location,
            'status': checkpoint.checkpoint_status.value,
            'params': checkpoint.params,
            'source_path': checkpoint.source_path,
            'target_path': checkpoint.target_path,
        }
    }
    logger.info(data)
