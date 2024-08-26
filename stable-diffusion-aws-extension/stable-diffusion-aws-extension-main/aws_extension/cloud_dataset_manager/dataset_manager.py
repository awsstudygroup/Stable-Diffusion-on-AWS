import logging
import sys

import requests

from utils import get_variable_from_json

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_sorted_cloud_dataset(username):
    url = get_variable_from_json("api_gateway_url") + "datasets?dataset_status=Enabled"
    api_key = get_variable_from_json("api_token")
    if not url or not api_key:
        logger.debug("Url or API-Key is not setting.")
        return []

    try:
        raw_response = requests.get(
            url=url,
            headers={
                "x-api-key": api_key,
                "username": username
            },
        )

        if raw_response.status_code != 200:
            logger.error(f"list_datasets: {raw_response.json()}")
            return []

        response = raw_response.json()
        logger.info(f"datasets response: {response}")
        datasets = response["data"]["datasets"]
        datasets.sort(
            key=lambda t: t["timestamp"] if "timestamp" in t else sys.float_info.max,
            reverse=True,
        )
        return datasets
    except Exception as e:
        logger.error(f"exception {e}")
        return []
