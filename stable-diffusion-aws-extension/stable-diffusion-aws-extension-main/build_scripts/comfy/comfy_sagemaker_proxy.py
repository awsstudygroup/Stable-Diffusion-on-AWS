import base64
import datetime
import json
import logging
import os
import sys
import tarfile
import time
import uuid
import gc
from dataclasses import dataclass
from typing import Optional

import boto3
import execution
import server
import folder_paths
from aiohttp import web
from boto3.dynamodb.conditions import Key
import comfy

global need_sync
global prompt_id
global executing
executing = False

global reboot
reboot = False

global last_call_time
last_call_time = None
global gc_triggered
gc_triggered = False

REGION = os.environ.get('AWS_REGION')
BUCKET = os.environ.get('S3_BUCKET_NAME')
QUEUE_URL = os.environ.get('COMFY_QUEUE_URL')

GEN_INSTANCE_ID = os.environ.get('ENDPOINT_INSTANCE_ID') if 'ENDPOINT_INSTANCE_ID' in os.environ and os.environ.get('ENDPOINT_INSTANCE_ID') else str(uuid.uuid4())
ENDPOINT_NAME = os.environ.get('ENDPOINT_NAME')
ENDPOINT_ID = os.environ.get('ENDPOINT_ID')

INSTANCE_MONITOR_TABLE_NAME = os.environ.get('COMFY_INSTANCE_MONITOR_TABLE')
SYNC_TABLE_NAME = os.environ.get('COMFY_SYNC_TABLE')

dynamodb = boto3.resource('dynamodb', region_name=REGION)
sync_table = dynamodb.Table(SYNC_TABLE_NAME)
instance_monitor_table = dynamodb.Table(INSTANCE_MONITOR_TABLE_NAME)

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.INFO)

ROOT_PATH = '/home/ubuntu/ComfyUI'
sqs_client = boto3.client('sqs', region_name=REGION)

GC_WAIT_TIME = 1800


def print_env():
    for key, value in os.environ.items():
        logger.info(f"{key}: {value}")


@dataclass
class ComfyResponse:
    statusCode: int
    message: str
    body: Optional[dict]


def ok(body: dict):
    return web.Response(status=200, content_type='application/json', body=json.dumps(body))


def error(body: dict):
    # TODO 500 -》200 because of need resp anyway not exception
    return web.Response(status=200, content_type='application/json', body=json.dumps(body))


def sen_sqs_msg(message_body, prompt_id_key):
    response = sqs_client.send_message(
        QueueUrl=QUEUE_URL,
        MessageBody=json.dumps(message_body),
        MessageGroupId=prompt_id_key
    )
    message_id = response['MessageId']
    return message_id


def sen_finish_sqs_msg(prompt_id_key):
    global need_sync
    # logger.info(f"sen_finish_sqs_msg start... {need_sync},{prompt_id_key}")
    if need_sync and QUEUE_URL and REGION:
        message_body = {'prompt_id': prompt_id_key, 'event': 'finish', 'data': {"node": None, "prompt_id": prompt_id_key},
                        'sid': None}
        message_id = sen_sqs_msg(message_body, prompt_id_key)
        logger.info(f"finish message sent {message_id}")


async def prepare_comfy_env(sync_item: dict):
    try:
        request_id = sync_item['request_id']
        logger.info(f"prepare_environment start sync_item:{sync_item}")
        prepare_type = sync_item['prepare_type']
        rlt = True
        if prepare_type in ['default', 'models']:
            sync_models_rlt = sync_s3_files_or_folders_to_local(f'{request_id}/models/*', f'{ROOT_PATH}/models', False)
            if not sync_models_rlt:
                rlt = False
        if prepare_type in ['default', 'inputs']:
            sync_inputs_rlt = sync_s3_files_or_folders_to_local(f'{request_id}/input/*', f'{ROOT_PATH}/input', False)
            if not sync_inputs_rlt:
                rlt = False
        if prepare_type in ['default', 'nodes']:
            sync_nodes_rlt = sync_s3_files_or_folders_to_local(f'{request_id}/custom_nodes/*',
                                                               f'{ROOT_PATH}/custom_nodes', True)
            if not sync_nodes_rlt:
                rlt = False
        if prepare_type == 'custom':
            sync_source_path = sync_item['s3_source_path']
            local_target_path = sync_item['local_target_path']
            if not sync_source_path or not local_target_path:
                logger.info("s3_source_path and local_target_path should not be empty")
            else:
                sync_rlt = sync_s3_files_or_folders_to_local(sync_source_path,
                                                             f'{ROOT_PATH}/{local_target_path}', False)
                if not sync_rlt:
                    rlt = False
        elif prepare_type == 'other':
            sync_script = sync_item['sync_script']
            logger.info("sync_script")
            # sync_script.startswith('s5cmd') 不允许
            try:
                if sync_script and (sync_script.startswith("python3 -m pip") or sync_script.startswith("python -m pip")
                                    or sync_script.startswith("pip install") or sync_script.startswith("apt")
                                    or sync_script.startswith("os.environ") or sync_script.startswith("ls")
                                    or sync_script.startswith("env") or sync_script.startswith("source")
                                    or sync_script.startswith("curl") or sync_script.startswith("wget")
                                    or sync_script.startswith("print") or sync_script.startswith("cat")
                                    or sync_script.startswith("sudo chmod") or sync_script.startswith("chmod")
                                    or sync_script.startswith("/home/ubuntu/ComfyUI/venv/bin/python")):
                    os.system(sync_script)
                elif sync_script and (sync_script.startswith("export ") and len(sync_script.split(" ")) > 2):
                    sync_script_key = sync_script.split(" ")[1]
                    sync_script_value = sync_script.split(" ")[2]
                    os.environ[sync_script_key] = sync_script_value
                    logger.info(os.environ.get(sync_script_key))
            except Exception as e:
                logger.error(f"Exception while execute sync_scripts : {sync_script}")
                rlt = False
        need_reboot = True if ('need_reboot' in sync_item and sync_item['need_reboot']
                               and str(sync_item['need_reboot']).lower() == 'true')else False
        global reboot
        reboot = need_reboot
        if need_reboot:
            os.environ['NEED_REBOOT'] = 'true'
        else:
            os.environ['NEED_REBOOT'] = 'false'
        logger.info("prepare_environment end")
        os.environ['LAST_SYNC_REQUEST_ID'] = sync_item['request_id']
        os.environ['LAST_SYNC_REQUEST_TIME'] = str(sync_item['request_time'])
        return rlt
    except Exception as e:
        return False


def sync_s3_files_or_folders_to_local(s3_path, local_path, need_un_tar):
    logger.info("sync_s3_models_or_inputs_to_local start")
    # s5cmd_command = f'{ROOT_PATH}/tools/s5cmd sync "s3://{bucket_name}/{s3_path}/*" "{local_path}/"'
    if need_un_tar:
        s5cmd_command = f's5cmd sync "s3://{BUCKET}/comfy/{ENDPOINT_NAME}/{s3_path}" "{local_path}/"'
    else:
        s5cmd_command = f's5cmd sync --delete=true "s3://{BUCKET}/comfy/{ENDPOINT_NAME}/{s3_path}" "{local_path}/"'
    # s5cmd_command = f's5cmd sync --delete=true "s3://{BUCKET}/comfy/{ENDPOINT_NAME}/{s3_path}" "{local_path}/"'
    # s5cmd_command = f's5cmd sync "s3://{BUCKET}/comfy/{ENDPOINT_NAME}/{s3_path}" "{local_path}/"'
    try:
        logger.info(s5cmd_command)
        os.system(s5cmd_command)
        logger.info(f'Files copied from "s3://{BUCKET}/comfy/{ENDPOINT_NAME}/{s3_path}" to "{local_path}/"')
        if need_un_tar:
            for filename in os.listdir(local_path):
                if filename.endswith(".tar.gz"):
                    tar_filepath = os.path.join(local_path, filename)
                    # extract_path = os.path.splitext(os.path.splitext(tar_filepath)[0])[0]
                    # os.makedirs(extract_path, exist_ok=True)
                    # logger.info(f'Extracting extract_path is {extract_path}')

                    with tarfile.open(tar_filepath, "r:gz") as tar:
                        for member in tar.getmembers():
                            tar.extract(member, path=local_path)
                    os.remove(tar_filepath)
                    logger.info(f'File {tar_filepath} extracted and removed')
        return True
    except Exception as e:
        logger.info(f"Error executing s5cmd command: {e}")
        return False


def sync_local_outputs_to_s3(s3_path, local_path):
    logger.info("sync_local_outputs_to_s3 start")
    s5cmd_command = f's5cmd sync "{local_path}/*" "s3://{BUCKET}/comfy/{s3_path}/" '
    try:
        logger.info(s5cmd_command)
        os.system(s5cmd_command)
        logger.info(f'Files copied local to "s3://{BUCKET}/comfy/{s3_path}/" to "{local_path}/"')
        clean_cmd = f'rm -rf {local_path}'
        os.system(clean_cmd)
        logger.info(f'Files removed from local {local_path}')
    except Exception as e:
        logger.info(f"Error executing s5cmd command: {e}")


def sync_local_outputs_to_base64(local_path):
    logger.info("sync_local_outputs_to_base64 start")
    try:
        result = {}
        for root, dirs, files in os.walk(local_path):
            for file in files:
                file_path = os.path.join(root, file)
                with open(file_path, "rb") as f:
                    file_content = f.read()
                    base64_content = base64.b64encode(file_content).decode('utf-8')
                    result[file] = base64_content
        clean_cmd = f'rm -rf {local_path}'
        os.system(clean_cmd)
        logger.info(f'Files removed from local {local_path}')
        return result
    except Exception as e:
        logger.info(f"Error executing s5cmd command: {e}")
        return {}


@server.PromptServer.instance.routes.post("/execute_proxy")
async def execute_proxy(request):
    json_data = await request.json()
    if 'out_path' in json_data and json_data['out_path'] is not None:
        out_path = json_data['out_path']
    else:
        out_path = None
    logger.info(f"invocations start json_data:{json_data}")
    global need_sync
    need_sync = json_data["need_sync"]
    global prompt_id
    prompt_id = json_data["prompt_id"]
    try:
        global executing
        if executing is True:
            resp = {"prompt_id": prompt_id, "instance_id": GEN_INSTANCE_ID, "status": "fail",
                    "message": "the environment is not ready valid[0] is false, need to resync"}
            sen_finish_sqs_msg(prompt_id)
            return error(resp)
        executing = True
        logger.info(
            f'bucket_name: {BUCKET}, region: {REGION}')
        if ('need_prepare' in json_data and json_data['need_prepare']
                and 'prepare_props' in json_data and json_data['prepare_props']):
            sync_already = await prepare_comfy_env(json_data['prepare_props'])
            if not sync_already:
                resp = {"prompt_id": prompt_id, "instance_id": GEN_INSTANCE_ID, "status": "fail",
                        "message": "the environment is not ready with sync"}
                executing = False
                sen_finish_sqs_msg(prompt_id)
                return error(resp)
        server_instance = server.PromptServer.instance
        if "number" in json_data:
            number = float(json_data['number'])
            server_instance.number = number
        else:
            number = server_instance.number
            if "front" in json_data:
                if json_data['front']:
                    number = -number
            server_instance.number += 1
        valid = execution.validate_prompt(json_data['prompt'])
        logger.info(f"Validating prompt result is {valid}")
        if not valid[0]:
            resp = {"prompt_id": prompt_id, "instance_id": GEN_INSTANCE_ID, "status": "fail",
                    "message": "the environment is not ready valid[0] is false, need to resync"}
            executing = False
            response = {"prompt_id": prompt_id, "number": number, "node_errors": valid[3]}
            sen_finish_sqs_msg(prompt_id)
            return error(resp)
        # if len(valid) == 4 and len(valid[3]) > 0:
        #     logger.info(f"Validating prompt error there is something error because of :valid: {valid}")
        #     resp = {"prompt_id": prompt_id, "instance_id": GEN_INSTANCE_ID, "status": "fail",
        #             "message": f"the valid is error, need to resync or check the workflow :{valid}"}
        #     executing = False
        #     return error(resp)
        extra_data = {}
        client_id = ''
        if "extra_data" in json_data:
            extra_data = json_data["extra_data"]
            if 'client_id' in extra_data and extra_data['client_id']:
                client_id = extra_data['client_id']
        if "client_id" in json_data and json_data["client_id"]:
            extra_data["client_id"] = json_data["client_id"]
            client_id = json_data["client_id"]

        server_instance.client_id = client_id

        prompt_id = json_data['prompt_id']
        server_instance.last_prompt_id = prompt_id
        e = execution.PromptExecutor(server_instance)
        outputs_to_execute = valid[2]
        e.execute(json_data['prompt'], prompt_id, extra_data, outputs_to_execute)

        s3_out_path = f'output/{prompt_id}/{out_path}' if out_path is not None else f'output/{prompt_id}'
        s3_temp_path = f'temp/{prompt_id}/{out_path}' if out_path is not None else f'temp/{prompt_id}'
        local_out_path = f'{ROOT_PATH}/output/{out_path}' if out_path is not None else f'{ROOT_PATH}/output'
        local_temp_path = f'{ROOT_PATH}/temp/{out_path}' if out_path is not None else f'{ROOT_PATH}/temp'

        logger.info(f"s3_out_path is {s3_out_path} and s3_temp_path is {s3_temp_path} and local_out_path is {local_out_path} and local_temp_path is {local_temp_path}")

        sync_local_outputs_to_s3(s3_out_path, local_out_path)
        sync_local_outputs_to_s3(s3_temp_path, local_temp_path)

        response_body = {
            "prompt_id": prompt_id,
            "instance_id": GEN_INSTANCE_ID,
            "status": "success",
            "output_path": f's3://{BUCKET}/comfy/{s3_out_path}',
            "temp_path": f's3://{BUCKET}/comfy/{s3_temp_path}',
        }
        sen_finish_sqs_msg(prompt_id)
        logger.info(f"execute inference response is {response_body}")
        executing = False
        return ok(response_body)
    except Exception as ecp:
        logger.info(f"exception occurred {ecp}")
        resp = {"prompt_id": prompt_id, "instance_id": GEN_INSTANCE_ID, "status": "fail",
                "message": f"exception occurred {ecp}"}
        executing = False
        return error(resp)
    finally:
        logger.info(f"gc check: {time.time()}")
        try:
            global last_call_time, gc_triggered
            gc_triggered = False
            if last_call_time is None:
                logger.info(f"gc check last time is NONE")
                last_call_time = time.time()
            else:
                if time.time() - last_call_time > GC_WAIT_TIME:
                    if not gc_triggered:
                        logger.info(f"gc start: {time.time()} - {last_call_time}")
                        e.reset()
                        comfy.model_management.cleanup_models()
                        gc.collect()
                        comfy.model_management.soft_empty_cache()
                        gc_triggered = True
                        logger.info(f"gc end: {time.time()} - {last_call_time}")
                    last_call_time = time.time()
                else:
                    last_call_time = time.time()
            logger.info(f"gc check end: {time.time()}")
        except Exception as e:
            logger.info(f"gc error: {e}")


def get_last_ddb_sync_record():
    sync_response = sync_table.query(
        KeyConditionExpression=Key('endpoint_name').eq(ENDPOINT_NAME),
        Limit=1,
        ScanIndexForward=False
    )
    latest_sync_record = sync_response['Items'][0] if ('Items' in sync_response
                                                       and len(sync_response['Items']) > 0) else None
    if latest_sync_record:
        logger.info(f"latest_sync_record is：{latest_sync_record}")
        return latest_sync_record

    logger.info("no latest_sync_record found")
    return None


def get_latest_ddb_instance_monitor_record():
    key_condition_expression = ('endpoint_name = :endpoint_name_val '
                                'AND gen_instance_id = :gen_instance_id_val')
    expression_attribute_values = {
        ':endpoint_name_val': ENDPOINT_NAME,
        ':gen_instance_id_val': GEN_INSTANCE_ID
    }
    instance_monitor_response = instance_monitor_table.query(
        KeyConditionExpression=key_condition_expression,
        ExpressionAttributeValues=expression_attribute_values
    )
    instance_monitor_record = instance_monitor_response['Items'][0] \
        if ('Items' in instance_monitor_response and len(instance_monitor_response['Items']) > 0) else None

    if instance_monitor_record:
        logger.info(f"instance_monitor_record is {instance_monitor_record}")
        return instance_monitor_record

    logger.info("no instance_monitor_record found")
    return None


def save_sync_instance_monitor(last_sync_request_id: str, sync_status: str):
    item = {
        'endpoint_id': ENDPOINT_ID,
        'endpoint_name': ENDPOINT_NAME,
        'gen_instance_id': GEN_INSTANCE_ID,
        'sync_status': sync_status,
        'last_sync_request_id': last_sync_request_id,
        'last_sync_time': datetime.datetime.now().isoformat(),
        'sync_list': [],
        'create_time': datetime.datetime.now().isoformat(),
        'last_heartbeat_time': datetime.datetime.now().isoformat()
    }
    save_resp = instance_monitor_table.put_item(Item=item)
    logger.info(f"save instance item {save_resp}")
    return save_resp


def update_sync_instance_monitor(instance_monitor_record):
    # 更新记录
    update_expression = ("SET sync_status = :new_sync_status, last_sync_request_id = :sync_request_id, "
                         "sync_list = :sync_list, last_sync_time = :sync_time, last_heartbeat_time = :heartbeat_time")
    expression_attribute_values = {
        ":new_sync_status": instance_monitor_record['sync_status'],
        ":sync_request_id": instance_monitor_record['last_sync_request_id'],
        ":sync_list": instance_monitor_record['sync_list'],
        ":sync_time": datetime.datetime.now().isoformat(),
        ":heartbeat_time": datetime.datetime.now().isoformat(),
    }

    response = instance_monitor_table.update_item(
        Key={'endpoint_name': ENDPOINT_NAME,
             'gen_instance_id': GEN_INSTANCE_ID},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_attribute_values
    )
    logger.info(f"update_sync_instance_monitor :{response}")
    return response


def sync_instance_monitor_status(need_save: bool):
    try:
        logger.info(f"sync_instance_monitor_status {datetime.datetime.now()}")
        if need_save:
            save_sync_instance_monitor('', 'init')
        else:
            update_expression = ("SET last_heartbeat_time = :heartbeat_time")
            expression_attribute_values = {
                ":heartbeat_time": datetime.datetime.now().isoformat(),
            }
            instance_monitor_table.update_item(
                Key={'endpoint_name': ENDPOINT_NAME,
                     'gen_instance_id': GEN_INSTANCE_ID},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values
            )
    except Exception as e:
        logger.info(f"sync_instance_monitor_status error :{e}")


@server.PromptServer.instance.routes.post("/reboot")
async def restart(self):
    logger.debug(f"start to reboot!!!!!!!! {self}")
    global executing
    if executing is True:
        logger.info(f"other inference doing cannot reboot!!!!!!!!")
        return ok({"message": "other inference doing cannot reboot"})
    need_reboot = os.environ.get('NEED_REBOOT')
    if need_reboot and need_reboot.lower() != 'true':
        logger.info("no need to reboot by os")
        return ok({"message": "no need to reboot by os"})
    global reboot
    if reboot is False:
        logger.info("no need to reboot by global constant")
        return ok({"message": "no need to reboot by constant"})

    logger.debug("rebooting !!!!!!!!")
    try:
        sys.stdout.close_log()
    except Exception as e:
        logger.info(f"error reboot!!!!!!!! {e}")
        pass
    return os.execv(sys.executable, [sys.executable] + sys.argv)


# must be sync invoke and use the env to check
@server.PromptServer.instance.routes.post("/sync_instance")
async def sync_instance(request):
    if not BUCKET:
        logger.error("No bucket provided ,wait and try again")
        resp = {"status": "success", "message": "syncing"}
        return ok(resp)

    if 'ALREADY_SYNC' in os.environ and os.environ.get('ALREADY_SYNC').lower() == 'false':
        resp = {"status": "success", "message": "syncing"}
        logger.error("other process doing ,wait and try again")
        return ok(resp)

    os.environ['ALREADY_SYNC'] = 'false'
    logger.info(f"sync_instance start ！！ {datetime.datetime.now().isoformat()} {request}")
    try:
        last_sync_record = get_last_ddb_sync_record()
        if not last_sync_record:
            logger.info("no last sync record found do not need sync")
            sync_instance_monitor_status(True)
            resp = {"status": "success", "message": "no sync"}
            os.environ['ALREADY_SYNC'] = 'true'
            return ok(resp)

        if ('request_id' in last_sync_record and last_sync_record['request_id']
                and os.environ.get('LAST_SYNC_REQUEST_ID')
                and os.environ.get('LAST_SYNC_REQUEST_ID') == last_sync_record['request_id']
                and os.environ.get('LAST_SYNC_REQUEST_TIME')
                and os.environ.get('LAST_SYNC_REQUEST_TIME') == str(last_sync_record['request_time'])):
            logger.info("last sync record already sync by os check")
            sync_instance_monitor_status(False)
            resp = {"status": "success", "message": "no sync env"}
            os.environ['ALREADY_SYNC'] = 'true'
            return ok(resp)

        instance_monitor_record = get_latest_ddb_instance_monitor_record()
        if not instance_monitor_record:
            sync_already = await prepare_comfy_env(last_sync_record)
            if sync_already:
                logger.info("should init prepare instance_monitor_record")
                sync_status = 'success' if sync_already else 'failed'
                save_sync_instance_monitor(last_sync_record['request_id'], sync_status)
            else:
                sync_instance_monitor_status(False)
        else:
            if ('last_sync_request_id' in instance_monitor_record
                    and instance_monitor_record['last_sync_request_id']
                    and instance_monitor_record['last_sync_request_id'] == last_sync_record['request_id']
                    and instance_monitor_record['sync_status']
                    and instance_monitor_record['sync_status'] == 'success'
                    and os.environ.get('LAST_SYNC_REQUEST_TIME')
                    and os.environ.get('LAST_SYNC_REQUEST_TIME') == str(last_sync_record['request_time'])):
                logger.info("last sync record already sync")
                sync_instance_monitor_status(False)
                resp = {"status": "success", "message": "no sync ddb"}
                os.environ['ALREADY_SYNC'] = 'true'
                return ok(resp)

            sync_already = await prepare_comfy_env(last_sync_record)
            instance_monitor_record['sync_status'] = 'success' if sync_already else 'failed'
            instance_monitor_record['last_sync_request_id'] = last_sync_record['request_id']
            sync_list = instance_monitor_record['sync_list'] if ('sync_list' in instance_monitor_record
                                                                 and instance_monitor_record['sync_list']) else []
            sync_list.append(last_sync_record['request_id'])

            instance_monitor_record['sync_list'] = sync_list
            logger.info("should update prepare instance_monitor_record")
            update_sync_instance_monitor(instance_monitor_record)
        os.environ['ALREADY_SYNC'] = 'true'
        resp = {"status": "success", "message": "sync"}
        return ok(resp)
    except Exception as e:
        logger.info("exception occurred", e)
        os.environ['ALREADY_SYNC'] = 'true'
        resp = {"status": "fail", "message": "sync"}
        return error(resp)


def validate_prompt_proxy(func):
    def wrapper(*args, **kwargs):
        logger.info("validate_prompt_proxy start...")
        result = func(*args, **kwargs)
        logger.info("validate_prompt_proxy end...")
        return result

    return wrapper


execution.validate_prompt = validate_prompt_proxy(execution.validate_prompt)


def send_sync_proxy(func):
    def wrapper(*args, **kwargs):
        logger.debug(f"Sending sync request!!!!!!! {args}")
        global need_sync
        global prompt_id
        logger.info(f"send_sync_proxy start... {need_sync},{prompt_id} {args}")
        func(*args, **kwargs)
        if need_sync and QUEUE_URL and REGION:
            logger.debug(f"send_sync_proxy params... {QUEUE_URL},{REGION},{need_sync},{prompt_id}")
            event = args[1]
            data = args[2]
            sid = args[3] if len(args) == 4 else None
            message_body = {'prompt_id': prompt_id, 'event': event, 'data': data, 'sid': sid}
            message_id = sen_sqs_msg(message_body, prompt_id)
            logger.info(f'send_sync_proxy message_id :{message_id} message_body: {message_body}')
        logger.debug(f"send_sync_proxy end...")

    return wrapper


server.PromptServer.send_sync = send_sync_proxy(server.PromptServer.send_sync)


def get_save_imge_path_proxy(func):
    def wrapper(*args, **kwargs):
        logger.info(f"get_save_imge_path_proxy args : {args} kwargs : {kwargs}")
        full_output_folder, filename, counter, subfolder, filename_prefix = func(*args, **kwargs)
        global prompt_id
        filename_prefix_new = filename_prefix + "_" + str(prompt_id)
        logger.info(f"get_save_imge_path_proxy filename_prefix new : {filename_prefix_new}")
        return full_output_folder, filename, counter, subfolder, filename_prefix_new

    return wrapper


folder_paths.get_save_image_path = get_save_imge_path_proxy(folder_paths.get_save_image_path)
