from dataclasses import dataclass
from typing import Optional, List, Any

from libs.enums import ComfyEnvPrepareType, ComfySyncStatus


@dataclass
class InferenceResult:
    instance_id: str
    status: str
    prompt_id: str
    start_time: Optional[str] = None
    message: Optional[str] = None
    output_path: Optional[str] = None
    output_files: Optional[List[str]] = None
    temp_path: Optional[str] = None
    temp_files: Optional[List[str]] = None
    endpoint_instance_id: Optional[str] = None
    workflow: Optional[str] = None
    endpoint_name: Optional[str] = None
    device_id: Optional[int] = None


@dataclass
class ComfyExecuteTable:
    prompt_id: str
    status: str
    # prompt: str number: Optional[int] front: Optional[str] extra_data: Optional[str] client_id: Optional[str]
    prompt_params: dict[str, Any]
    create_time: Optional[str] = None
    prompt_path: Optional[str] = None
    instance_id: Optional[str] = None
    start_time: Optional[Any] = ''
    complete_time: Optional[Any] = None
    sagemaker_raw: Optional[Any] = None
    output_path: Optional[str] = None
    message: Optional[str] = None
    device_id: Optional[str] = None
    endpoint_instance_id: Optional[str] = None
    output_files: Optional[List[str]] = None
    temp_path: Optional[str] = ''
    temp_files: Optional[List[str]] = ''
    multi_async: Optional[bool] = False
    batch_id: Optional[str] = None
    endpoint_name: Optional[str] = None
    inference_type: Optional[str] = None
    workflow: Optional[str] = None
    need_sync: Optional[bool] = None
    prompt_params: Optional[dict[str, Any]] = None


@dataclass
class ComfySyncTable:
    request_id: str
    endpoint_name: str
    endpoint_id: str
    instance_count: int
    prepare_type: ComfyEnvPrepareType
    need_reboot: bool
    s3_source_path: Optional[str]
    local_target_path: Optional[str]
    sync_script: Optional[str]
    endpoint_snapshot: Optional[Any]
    request_time: int
    request_time_str: str


@dataclass
class ComfyInstanceMonitorTable:
    endpoint_id: str
    endpoint_name: str
    gen_instance_id: str
    sync_status: ComfySyncStatus
    last_sync_request_id: str
    last_sync_time: str
    # period_config: str  move to config table
    sync_list: Optional[List[str]]
    create_time: str
    last_heartbeat_time: str


@dataclass
class ComfyMessageTable:
    prompt_id: str
    request_time: str
    message_body: str
