import datetime
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

import boto3
import sagemaker
import tomli
import tomli_w
from aws_lambda_powertools import Tracer

from checkpoints.create_checkpoint import check_ckpt_name_unique
from common import const
from common.const import LoraTrainType, PERMISSION_TRAIN_ALL
from common.ddb_service.client import DynamoDbUtilsService
from common.excepts import BadRequestException
from common.response import (
    created,
)
from common.util import query_data
from libs.common_tools import DecimalEncoder
from libs.data_types import (
    TrainJob,
    TrainJobStatus,
)
from libs.utils import get_user_roles, permissions_check, response_error, log_json

tracer = Tracer()
bucket_name = os.environ.get("S3_BUCKET_NAME")
train_table = os.environ.get("TRAIN_TABLE")
checkpoint_table = os.environ.get("CHECKPOINT_TABLE")
user_table = os.environ.get("MULTI_USER_TABLE")
dataset_info_table = os.environ.get("DATASET_INFO_TABLE")
esd_version = os.environ.get("ESD_VERSION")
instance_type = os.environ.get("INSTANCE_TYPE")
sagemaker_role_arn = os.environ.get("TRAIN_JOB_ROLE")

account_id = os.environ.get("ACCOUNT_ID")
region = os.environ.get("AWS_REGION")
url_suffix = os.environ.get("URL_SUFFIX")

image_uri = f"{account_id}.dkr.ecr.{region}.{url_suffix}/esd-training:{esd_version}"

ddb_client = boto3.client('dynamodb')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL") or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)
s3 = boto3.client("s3", region_name=region)


@dataclass
class Event:
    params: dict[str, Any]
    lora_train_type: Optional[str] = LoraTrainType.KOHYA.value


def _update_toml_file_in_s3(bucket_name: str, file_key: str, new_file_key: str, updated_params):
    """Update and save a TOML file in an S3 bucket

    Args:
        bucket_name (str): S3 bucket name to save the TOML file
        file_key (str): TOML template file key
        new_file_key (str): TOML file with merged parameters
        updated_params (_type_): parameters to be merged
    """
    try:
        response = s3.get_object(Bucket=bucket_name, Key=file_key)
        toml_content = response["Body"].read().decode("utf-8")
        toml_data = tomli.loads(toml_content)

        # Update parameters in the TOML data
        for section, params in updated_params.items():
            if section in toml_data:
                for key, value in params.items():
                    toml_data[section][key] = value
            else:
                toml_data[section] = params

        updated_toml_content = tomli_w.dumps(toml_data)
        s3.put_object(Bucket=bucket_name, Key=new_file_key, Body=updated_toml_content)
        logger.info(f"Updated '{file_key}' in '{bucket_name}' successfully.")

    except Exception as e:
        logger.error(f"An error occurred when updating Kohya toml: {e}")


def _trigger_sagemaker_training_job(
        train_job: TrainJob, ckpt_output_path: str, train_job_name: str
):
    """Trigger a SageMaker training job

    Args:
        train_job (TrainJob): training job metadata
        ckpt_output_path (str): S3 path to store the trained model file
        train_job_name (str): training job name
    """

    site_packages_s3_path = (f"s3://aws-gcr-solutions-{region}/"
                             f"stable-diffusion-aws-extension-github-mainline/{esd_version}/site-packages.tar")

    data = {
        "id": train_job.id,
        "training_id": train_job.id,
        "sagemaker_program": "extensions/sd-webui-sagemaker/sagemaker_entrypoint_json.py",
        "params": train_job.params,
        "s3-input-path": train_job.input_s3_location,
        "s3-output-path": ckpt_output_path,
        "training-type": train_job.params[
            "training_type"
        ],  # Available value: "kohya"
    }

    train_params_file = f"train/param-{train_job.id}.json"

    s3.put_object(Bucket=bucket_name, Key=train_params_file, Body=json.dumps(data, indent=4, cls=DecimalEncoder))

    final_instance_type = instance_type
    if (
            "training_params" in train_job.params
            and "training_instance_type" in train_job.params["training_params"]
            and train_job.params["training_params"]["training_instance_type"]
    ):
        final_instance_type = train_job.params["training_params"][
            "training_instance_type"
        ]

    est = sagemaker.estimator.Estimator(
        image_uri,
        sagemaker_role_arn,
        instance_count=1,
        instance_type=final_instance_type,
        volume_size=125,
        base_job_name=f"{train_job_name}",
        hyperparameters={
            "s3_location": f"s3://{bucket_name}/{train_params_file}",
        },
        job_id=train_job.id,
        environment={
            "SITE_PACKAGES_S3_PATH": site_packages_s3_path
        }
    )
    est.fit(wait=False)

    while not est._current_job_name:
        time.sleep(1)

    train_job.sagemaker_train_name = est._current_job_name

    search_key = {"id": train_job.id}
    ddb_service.update_item(
        table=train_table,
        key=search_key,
        field_name="sagemaker_train_name",
        value=est._current_job_name,
    )
    train_job.job_status = TrainJobStatus.Training
    ddb_service.update_item(
        table=train_table,
        key=search_key,
        field_name="job_status",
        value=TrainJobStatus.Starting.value,
    )


def _start_training_job(job: TrainJob):
    s3_location = f"s3://{bucket_name}/Stable-diffusion/checkpoint/custom/{job.id}"

    _trigger_sagemaker_training_job(job, s3_location, job.model_id)

    return {
        "id": job.id,
        "status": job.job_status.Starting.value,
        "created": str(job.timestamp),
        "params": job.params,
        "input_location": job.input_s3_location,
        "output_location": s3_location
    }


def get_model_location(model_name):
    resp = ddb_client.scan(
        TableName=checkpoint_table,
    )

    for item in resp['Items']:
        if 'checkpoint_names' not in item:
            continue
        if 'L' not in item['checkpoint_names']:
            continue
        if len(item['checkpoint_names']['L']) == 0:
            continue
        if item['checkpoint_names']['L'][0]['S'] == model_name:
            return f'{item["s3_location"]["S"]}/{model_name}'

    raise BadRequestException("Model not found")


def get_dataset_location(dataset_name):
    dataset_items = ddb_service.query_items(table=dataset_info_table, key_values={
        'dataset_name': dataset_name,
    })

    if len(dataset_items) == 0:
        raise BadRequestException("Dataset not found")

    return f"s3://{bucket_name}/dataset/{dataset_name}"


def check_train_ckpt_name_unique(names: [str]):
    if len(names) == 0:
        return

    trains = ddb_service.scan(table=train_table)
    exists_names = []
    for train in trains:
        output_name = train['params']['M']['config_params']['M']['output_name']['S']
        exists_names.append(f"{output_name}.safetensors")

    logger.info(json.dumps(exists_names))

    for name in names:
        if name.strip() in exists_names:
            raise Exception(f'{name} already exists, '
                            f'please use another or rename/delete exists')


def _create_training_job(raw_event, context):
    """Create a training job

    Returns:
        Training job in JSON format
    """
    request_id = context.aws_request_id
    event = Event(**json.loads(raw_event["body"]))
    logger.info(json.dumps(json.loads(raw_event["body"])))
    _lora_train_type = event.lora_train_type

    username = permissions_check(raw_event, [PERMISSION_TRAIN_ALL])

    if _lora_train_type.lower() == LoraTrainType.KOHYA.value:
        # Kohya training
        base_key = f"{_lora_train_type.lower()}/train/{request_id}"
        input_location = f"{base_key}/input"

        model_name = query_data(event.params, ['training_params', 'model'])
        dataset_name = query_data(event.params, ['training_params', 'dataset'])
        fm_type = query_data(event.params, ['training_params', 'fm_type'])
        output_name = query_data(event.params, ['config_params', 'output_name'])
        output_name = f"{output_name}.safetensors"

        check_ckpt_name_unique([output_name])
        check_train_ckpt_name_unique([output_name])

        save_every_n_epochs = query_data(event.params, ['config_params', 'save_every_n_epochs'])
        event.params["config_params"]["save_every_n_epochs"] = int(save_every_n_epochs)

        max_train_epochs = query_data(event.params, ['config_params', 'max_train_epochs'])
        event.params["config_params"]["max_train_epochs"] = int(max_train_epochs)

        event.params["training_params"]["s3_model_path"] = get_model_location(model_name)
        del event.params['training_params']['model']

        event.params["training_params"]["s3_data_path"] = get_dataset_location(dataset_name)
        del event.params['training_params']['dataset']

        log_json('event', event.__dict__)

        if fm_type.lower() == const.TrainFMType.SD_1_5.value:
            toml_dest_path = f"{input_location}/{const.KOHYA_TOML_FILE_NAME}"
            toml_template_path = "template/" + const.KOHYA_TOML_FILE_NAME
        elif fm_type.lower() == const.TrainFMType.SD_XL.value:
            toml_dest_path = f"{input_location}/{const.KOHYA_XL_TOML_FILE_NAME}"
            toml_template_path = "template/" + const.KOHYA_XL_TOML_FILE_NAME
        else:
            raise BadRequestException(
                f"Invalid fm_type {fm_type}, the valid values are {const.TrainFMType.SD_1_5.value} "
                f"and {const.TrainFMType.SD_XL.value}"
            )

        # Merge user parameter, if no config_params is defined, use the default value in S3 bucket
        if "config_params" in event.params:
            updated_parameters = {
                'training': event.params["config_params"]
            }
            _update_toml_file_in_s3(
                bucket_name, toml_template_path, toml_dest_path, updated_parameters
            )
        else:
            # Copy template file and make no changes as no config parameters are defined
            s3.copy_object(
                CopySource={"Bucket": bucket_name, "Key": toml_template_path},
                Bucket=bucket_name,
                Key=toml_dest_path,
            )

        event.params["training_params"]["s3_toml_path"] = f"s3://{bucket_name}/{toml_dest_path}"
    else:
        raise BadRequestException(
            f"Invalid lora train type: {_lora_train_type}, the valid value is {LoraTrainType.KOHYA.value}."
        )

    event.params["training_type"] = _lora_train_type.lower()
    user_roles = get_user_roles(ddb_service, user_table, username)
    ckpt_type = const.CheckPointType.LORA
    if "config_params" in event.params and \
            "additional_network" in event.params["config_params"] and \
            "network_module" in event.params["config_params"]["additional_network"]:
        network_module = event.params["config_params"]["additional_network"]["network_module"]
        if network_module.lower() != const.NetworkModule.LORA:
            ckpt_type = const.CheckPointType.SD

    train_input_s3_location = f"s3://{bucket_name}/{input_location}"

    train_job = TrainJob(
        id=request_id,
        model_id=const.KOHYA_MODEL_ID,
        job_status=TrainJobStatus.Initial,
        params=event.params,
        train_type=const.TRAIN_TYPE,
        input_s3_location=train_input_s3_location,
        ckpt_type=ckpt_type,
        base_key=base_key,
        timestamp=datetime.datetime.now().timestamp(),
        allowed_roles_or_users=user_roles,
    )
    ddb_service.put_items(table=train_table, entries=train_job.__dict__)

    return train_job


@tracer.capture_lambda_handler
def handler(raw_event, context):
    job_id = None
    try:
        logger.info(json.dumps(raw_event))

        job = _create_training_job(raw_event, context)
        job_info = _start_training_job(job)

        return created(data=job_info, decimal=True)
    except Exception as e:
        if job_id:
            # Clean up the created job when an error occurs
            ddb_service.delete_item(train_table, keys={'id': job_id})
            ddb_service.delete_item(checkpoint_table, keys={'id': job_id})
        return response_error(e)
