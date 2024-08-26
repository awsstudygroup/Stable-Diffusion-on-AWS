from __future__ import print_function

import logging
import time
from datetime import datetime
from datetime import timedelta

import pytest

import config as config
from utils.api import Api
from utils.helper import endpoints_wait_for_in_service

logger = logging.getLogger(__name__)

endpoint_name = f"sd-real-time-{config.endpoint_name}"


@pytest.mark.skipif(config.is_gcr, reason="not ready in gcr")
@pytest.mark.skipif(config.test_fast, reason="test_fast")
class TestEndpointRealTimeCheckForTrainE2E:

    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()

    @classmethod
    def teardown_class(self):
        pass

    def test_1_list_real_time_endpoints_status(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        params = {
            "username": config.username
        }

        resp = self.api.list_endpoints(headers=headers, params=params)
        assert resp.status_code == 200, resp.dumps()

        endpoints = resp.json()['data']["endpoints"]
        assert len(endpoints) >= 0

        assert endpoint_name in [endpoint["endpoint_name"] for endpoint in endpoints]

        timeout = datetime.now() + timedelta(minutes=40)

        while datetime.now() < timeout:
            result = endpoints_wait_for_in_service(self.api, endpoint_name)
            if result:
                break
            time.sleep(15)
        else:
            raise Exception("Create Endpoint timed out after 40 minutes.")

