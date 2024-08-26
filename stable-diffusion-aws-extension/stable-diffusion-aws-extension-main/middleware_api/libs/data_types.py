import dataclasses
from dataclasses import dataclass
from typing import Optional, Any, List

import boto3.dynamodb.types

from libs.enums import CreateModelStatus, CheckPointStatus, TrainJobStatus, DataStatus, DatasetStatus

Default_Role = 'IT Operator'


@dataclass
class _PartitionKeys:
    user = 'user'
    role = 'role'


PARTITION_KEYS = _PartitionKeys()


@dataclasses.dataclass
class Model:
    id: str
    timestamp: float
    name: str
    checkpoint_id: str
    model_type: str
    job_status: CreateModelStatus
    output_s3_location: Optional[str] = ''
    params: Optional[dict[str, Any]] = None
    allowed_roles_or_users: Optional[list[str]] = None

    def __post_init__(self):
        if type(self.job_status) == str:
            self.job_status = CreateModelStatus[self.job_status]


@dataclasses.dataclass
class CheckPoint:
    id: str
    timestamp: float
    checkpoint_type: str
    s3_location: str
    checkpoint_status: CheckPointStatus
    allowed_roles_or_users: Optional[list[str]] = None
    version: str = 'v1.0'  # todo: this is for the future
    checkpoint_names: Optional[list[str]] = None  # the actual checkpoint file names
    params: Optional[dict[str, Any]] = None
    source_path: Optional[str] = None
    target_path: Optional[str] = None

    def __post_init__(self):
        if type(self.checkpoint_status) == str:
            self.checkpoint_status = CheckPointStatus[self.checkpoint_status]


@dataclasses.dataclass
class TrainJob:
    id: str
    timestamp: float
    model_id: str
    train_type: str
    job_status: TrainJobStatus
    input_s3_location: str
    sagemaker_train_name: Optional[str] = ''
    ckpt_type: Optional[str] = ''
    base_key: Optional[str] = ''
    params: Optional[dict[str, Any]] = None
    allowed_roles_or_users: Optional[list[str]] = None
    # todo will remove
    checkpoint_id: str = None
    sagemaker_sfn_arn: Optional[str] = None
    logs: Optional[List[str]] = None

    def __post_init__(self):
        if type(self.job_status) == str:
            self.job_status = TrainJobStatus[self.job_status]


@dataclasses.dataclass
class MultipartFileReq:
    filename: str
    parts_number: int


@dataclass
class BaseMultiUserEntity:
    kind: str
    sort_key: str
    creator: str


@dataclass
class User(BaseMultiUserEntity):
    roles: [str]
    params: Optional[dict[str, Any]] = None
    password: bytes = None

    def __post_init__(self):
        if type(self.password) in (boto3.dynamodb.types.Binary, boto3.dynamodb.types.BINARY):
            self.password = self.password.value


@dataclass
class Role(BaseMultiUserEntity):
    permissions: [str]
    params: Optional[dict[str, Any]] = None


@dataclass
class DatasetItem:
    dataset_name: str  # partition key (s3 key base, not include bucket name)
    sort_key: str  # sorted key: timestamp_name
    name: str  # data name (s3 object key)
    type: str  # data type
    data_status: DataStatus
    params: Optional[dict[str, Any]] = None
    allowed_roles_or_users: Optional[list[str]] = None

    def __post_init__(self):
        if type(self.data_status) == str:
            self.data_status = DataStatus[self.data_status]

    def get_s3_key(self, prefix: str = ""):
        if prefix:
            return f'dataset/{self.dataset_name}/{prefix}/{self.name}'

        return f'dataset/{self.dataset_name}/{self.name}'


@dataclass
class DatasetInfo:
    dataset_name: str  # primary key
    timestamp: float
    dataset_status: DatasetStatus
    params: Optional[dict[str, Any]] = None
    allowed_roles_or_users: Optional[list[str]] = None
    prefix: str = ""

    def __post_init__(self):
        if type(self.dataset_status) == str:
            self.dataset_status = DatasetStatus[self.dataset_status]

    def get_s3_key(self):
        if self.prefix:
            return f'dataset/{self.dataset_name}/{self.prefix}'

        return f'dataset/{self.dataset_name}'


@dataclass
class InferenceJob:
    InferenceJobId: str
    status: str
    taskType: str
    owner_group_or_role: Optional[List[str]] = None
    # todo will delete
    inference_info_name: Optional[Any] = None
    startTime: Optional[Any] = ''
    createTime: Optional[Any] = None
    image_names: Optional[Any] = None
    sagemakerRaw: Optional[Any] = None
    completeTime: Optional[Any] = None
    params: Optional[dict[str, Any]] = None
    inference_type: Optional[str] = None
    payload_string: Optional[str] = None
    workflow: Optional[str] = None


@dataclass
class Endpoint:
    EndpointDeploymentJobId: str
    autoscaling: bool = None
    max_instance_number: str = None
    startTime: str = None
    status: str = None  # deprecated, but can't remove, avoid unexpected keyword argument
    instance_type: str = None
    current_instance_count: str = None
    endTime: Optional[str] = None
    endpoint_status: Optional[str] = None
    endpoint_name: Optional[str] = None
    error: Optional[str] = None
    endpoint_type: Optional[str] = "Async"
    owner_group_or_role: Optional[List[str]] = None
    min_instance_number: str = None
    custom_extensions: str = ""
    service_type: str = ""


@dataclass
class Workflow:
    name: str
    s3_location: str
    image_uri: str
    status: str
    payload_json: str = ""
    size: str = ""
    create_time: Optional[Any] = None


@dataclass
class WorkflowSchema:
    name: str
    payload: str
    workflow: str = ""
    create_time: Optional[Any] = None


# a copy of aws_extensions.models.InvocationsRequest
@dataclass
class InvocationRequest:
    id: str
    task: str
    username: Optional[str]
    models: Optional[dict]
    param_s3: Optional[str] = None
    payload_string: Optional[str] = None
    workflow: Optional[str] = None
