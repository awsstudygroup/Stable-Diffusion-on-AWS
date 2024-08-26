from __future__ import print_function

import logging
import threading

import pytest

import config as config
from utils.api import Api
from utils.enums import InferenceType
from utils.helper import upload_with_put

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

headers = {
    "x-api-key": config.api_key,
    "username": config.username
}


def task_to_run(inference_id):
    t_name = threading.current_thread().name
    logger.info(f"Task is running on {t_name}, {inference_id}")

    api = Api(config)

    api.start_inference_job(job_id=inference_id, headers=headers)
    logger.info(f"start_inference_job: {inference_id}")


@pytest.mark.skipif(not config.is_local, reason="local test only")
class TestMutilTaskGPUs:
    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()

    @classmethod
    def teardown_class(self):
        pass

    def test_0_gpus_clear_inferences_jobs(self):
        resp = self.api.list_inferences(headers, params={"limit": 100})
        assert resp.status_code == 200, resp.dumps()
        inferences = resp.json()['data']['inferences']
        list = []
        for inference in inferences:
            list.append(inference['InferenceJobId'])
        data = {
            "inference_id_list": list
        }
        self.api.delete_inferences(data=data, headers=headers)

    def test_1_gpus_start_real_time_tps(self):
        ids = []
        for i in range(20):
            id = self.tps_real_time_create()
            logger.info(f"inference created: {id}")
            ids.append(id)

        threads = []
        for id in ids:
            thread = threading.Thread(target=task_to_run, args=(id,))
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

    def tps_real_time_create(self):
        data = {
            "inference_type": "Async",
            "task_type": InferenceType.TXT2IMG.value,
            "workflow": 'gpus',
            "models": {
                "Stable-diffusion": [config.default_model_id],
                "embeddings": []
            },
        }

        resp = self.api.create_inference(headers=headers, data=data)
        assert resp.status_code == 201, resp.dumps()

        inference_data = resp.json()['data']["inference"]

        upload_with_put(inference_data["api_params_s3_upload_url"], "./data/api_params/txt2img_api_param.json")

        return inference_data['id']
