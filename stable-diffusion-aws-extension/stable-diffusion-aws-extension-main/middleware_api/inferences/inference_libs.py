import base64
import io
import json
import logging
import os
from datetime import datetime

import boto3
from PIL import Image
from aws_lambda_powertools import Tracer

from common.util import upload_file_to_s3, record_queue_latency_metrics
from libs.enums import ServiceType
from libs.utils import log_json

tracer = Tracer()
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

sns = boto3.client('sns')
s3_client = boto3.client('s3')

ddb_client = boto3.resource('dynamodb')
inference_table = ddb_client.Table('SDInferenceJobTable')

S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')


@tracer.capture_method
def parse_sagemaker_result(sagemaker_out, create_time, inference_id, task_type, endpoint_name):
    update_inference_job_table(inference_id, 'completeTime', datetime.now().isoformat())

    try:
        # maybe start_time is not in the response
        record_queue_latency_metrics(create_time=create_time,
                                     start_time=sagemaker_out['start_time'],
                                     ep_name=endpoint_name,
                                     service=ServiceType.SD.value)
        if task_type in ["interrogate_clip", "interrogate_deepbooru"]:
            interrogate_clip_interrogate_deepbooru(sagemaker_out, inference_id)
        elif task_type in ["txt2img", "img2img"]:
            txt2_img_img(sagemaker_out, inference_id, endpoint_name)
        elif task_type in ["extra-single-image", "rembg"]:
            esi_rembg(sagemaker_out, inference_id, endpoint_name)

        update_inference_job_table(inference_id, 'status', 'succeed')
    except Exception as e:
        update_inference_job_table(inference_id, 'status', 'failed')
        raise e


def decode_base64_to_image(encoding):
    if encoding.startswith("data:image/"):
        encoding = encoding.split(";")[1].split(",")[1]
    return Image.open(io.BytesIO(base64.b64decode(encoding)))


def update_ddb_image(inference_id: str, image_name: str):
    inference_table.update_item(
        Key={
            'InferenceJobId': inference_id
        },
        UpdateExpression='SET image_names = list_append(if_not_exists(image_names, :empty_list), :new_image)',
        ExpressionAttributeValues={
            ':new_image': [image_name],
            ':empty_list': []
        }
    )


def get_bucket_and_key(s3uri):
    pos = s3uri.find('/', 5)
    bucket = s3uri[5: pos]
    key = s3uri[pos + 1:]
    return bucket, key


def update_inference_job_table(inference_id, key, value):
    logger.info(f"Update job with inference id: {inference_id}, key: {key}, value: {value}")
    try:
        inference_table.update_item(
            Key={
                "InferenceJobId": inference_id,
            },
            UpdateExpression=f"set #k = :r",
            ExpressionAttributeNames={'#k': key},
            ExpressionAttributeValues={':r': value},
            ConditionExpression="attribute_exists(InferenceJobId)",
            ReturnValues="UPDATED_NEW"
        )
    except Exception as e:
        logger.error(f"Update Inference job table error: {e}")
        raise e


def update_table_by_pk(table_name: str, pk: str, id: str, key: str, value):
    logger.info(f"Update {table_name} with {pk}: {id}, key: {key}, value: {value}")
    try:
        ddb_table = ddb_client.Table(table_name)
        ddb_table.update_item(
            Key={
                pk: id,
            },
            UpdateExpression=f"set #k = :r",
            ExpressionAttributeNames={'#k': key},
            ExpressionAttributeValues={':r': value},
            ConditionExpression=f"attribute_exists({pk})",
            ReturnValues="UPDATED_NEW"
        )
    except Exception as e:
        logger.error(f"Update {table_name} error: {e}")
        raise e


def esi_rembg(sagemaker_out, inference_id, endpoint_name):
    if 'image' not in sagemaker_out:
        raise Exception(sagemaker_out)

    image = Image.open(io.BytesIO(base64.b64decode(sagemaker_out["image"])))
    output = io.BytesIO()
    image.save(output, format="PNG")
    # Upload the image to the S3 bucket
    s3_client.put_object(
        Body=output.getvalue(),
        Bucket=S3_BUCKET_NAME,
        Key=f"out/{inference_id}/result/image.png"
    )

    update_ddb_image(inference_id, "image.png")

    save_inference_parameters(sagemaker_out, inference_id, endpoint_name)


def interrogate_clip_interrogate_deepbooru(sagemaker_out, inference_id):
    caption = sagemaker_out['caption']
    # Update the DynamoDB table for the caption
    inference_table.update_item(
        Key={
            'InferenceJobId': inference_id
        },
        UpdateExpression='SET caption=:f',
        ExpressionAttributeValues={
            ':f': caption,
        }
    )


def txt2_img_img(sagemaker_out, inference_id, endpoint_name):
    for count, b64image in enumerate(sagemaker_out["images"]):
        output_img_type = None
        if 'output_img_type' in sagemaker_out and sagemaker_out['output_img_type']:
            output_img_type = sagemaker_out['output_img_type']
            logger.info(f"handle_sagemaker_out: output_img_type is not null, {output_img_type}")
        if not output_img_type:
            image = decode_base64_to_image(b64image)
            output = io.BytesIO()
            image.save(output, format="PNG")
            s3_client.put_object(
                Body=output.getvalue(),
                Bucket=S3_BUCKET_NAME,
                Key=f"out/{inference_id}/result/image_{count}.png"
            )
        else:
            gif_data = base64.b64decode(b64image.split(",", 1)[0])
            if len(output_img_type) == 1 and (output_img_type[0] == 'PNG' or output_img_type[0] == 'TXT'):
                logger.debug(f'output_img_type len is 1 :{output_img_type[0]} {count}')
                img_type = 'png'
            elif len(output_img_type) == 2 and ('PNG' in output_img_type and 'TXT' in output_img_type):
                logger.debug(f'output_img_type len is 2 :{output_img_type[0]} {output_img_type[1]} {count}')
                img_type = 'png'
            else:
                img_type = 'gif'
                output_img_type = [element for element in output_img_type if
                                   "TXT" not in element and "PNG" not in element]
                logger.debug(f'output_img_type new is  :{output_img_type}  {count}')
                # type set
                image_count = len(sagemaker_out["images"])
                type_count = len(output_img_type)
                if image_count % type_count == 0:
                    idx = count % type_count
                    img_type = output_img_type[idx].lower()
            logger.debug(f'img_type is :{img_type} count is:{count}')
            s3_client.put_object(
                Body=gif_data,
                Bucket=S3_BUCKET_NAME,
                Key=f"out/{inference_id}/result/image_{count}.{img_type}"
            )

        update_ddb_image(inference_id, f"image_{count}.png")

    save_inference_parameters(sagemaker_out, inference_id, endpoint_name)


@tracer.capture_method
def save_inference_parameters(sagemaker_out, inference_id, endpoint_name):
    inference_parameters = {}

    if 'parameters' in sagemaker_out:
        inference_parameters["parameters"] = sagemaker_out["parameters"]

    if 'html_info' in sagemaker_out:
        inference_parameters["html_info"] = sagemaker_out["html_info"]

    if 'info' in sagemaker_out:
        inference_parameters["info"] = sagemaker_out["info"]

    inference_parameters["endpoint_name"] = endpoint_name
    inference_parameters["inference_id"] = inference_id

    json_file_name = f"/tmp/{inference_id}_param.json"

    with open(json_file_name, "w") as outfile:
        json.dump(inference_parameters, outfile)

    upload_file_to_s3(json_file_name, S3_BUCKET_NAME, f"out/{inference_id}/result",
                      f"{inference_id}_param.json")

    log_json(f"Complete inference parameters", inference_parameters)


@tracer.capture_method
def get_inference_job(inference_job_id):
    if not inference_job_id:
        logger.error("Invalid inference job id")
        raise ValueError("Inference job id must not be None or empty")

    response = inference_table.get_item(Key={'InferenceJobId': inference_job_id})

    logger.info(f"Get inference job response: {response}")

    if not response['Item']:
        logger.error(f"Inference job not found with id: {inference_job_id}")
        raise ValueError(f"Inference job not found with id: {inference_job_id}")
    return response['Item']
