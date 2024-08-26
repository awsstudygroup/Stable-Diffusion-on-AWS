from __future__ import print_function

import logging
import os
import threading
import time
import uuid

import pytest

import config as config
from utils.api import Api
from utils.helper import wget_file, comfy_execute_create, get_endpoint_comfy_async

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

headers = {
    "x-api-key": config.api_key,
    "username": config.username
}

id = str(uuid.uuid4())


@pytest.mark.skipif(not config.is_local, reason="local test only")
class TestComfyMutilGpusTasks:
    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()
        self.endpoint_name = get_endpoint_comfy_async(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_10_download_file(self):
        local_path = f"./data/comfy/models/checkpoints/v1-5-pruned-emaonly.ckpt"
        wget_file(
            local_path,
            'https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.ckpt'
        )

    def test_11_sync_files_to_comfy_endpoint(self):
        local = "'./data/comfy/models/*'"
        target = f"'s3://{config.bucket}/comfy/{self.endpoint_name}/{id}/models/'"
        logger.info(f"Syncing {local} to {target}")
        os.system(f"rm -rf ./s5cmd")
        os.system(f"wget -q ./ https://raw.githubusercontent.com/elonniu/s5cmd/main/s5cmd")
        os.system(f"chmod +x ./s5cmd")
        os.system(f"./s5cmd sync {local} {target}")

    def test_12_sync_files(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }
        data = {"endpoint_name": f"{self.endpoint_name}",
                "need_reboot": True,
                "prepare_id": id,
                "prepare_type": "models"}
        resp = self.api.prepare(data=data, headers=headers)
        assert resp.status_code == 200, resp.dumps()
        logger.info(resp.json())
        logger.info(f"wait 30s for endpoint sync files...")
        time.sleep(30)

    def test_13_clean_all_executes(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        while True:
            resp = self.api.list_executes(headers=headers, params={"limit": 20})
            executes = resp.json()['data']['executes']
            if len(executes) == 0:
                break

            execute_id_list = []
            i = 0
            for execute in executes:
                i = i + 1
                prompt_id = execute['prompt_id']
                execute_id_list.append(prompt_id)
                logger.info(f"delete execute {i} {prompt_id}")

            data = {
                "execute_id_list": execute_id_list,
            }
            resp = self.api.delete_executes(headers=headers, data=data)
            if resp.status_code == 400:
                logger.info(resp.json()['message'])
                time.sleep(5)
                continue

    def test_14_comfy_gpus_start_async_tps(self):
        threads = []
        gpus = 4
        batch = 1000
        for i in range(gpus):
            thread = threading.Thread(target=create_batch_executes, args=(batch, self.api, self.endpoint_name))
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()


def create_batch_executes(n, api, endpoint_name):
    for i in range(n):
        comfy_execute_create(n=i, api=api, endpoint_name=endpoint_name, wait_succeed=True)
