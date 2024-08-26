import json
import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

import boto3
from aws_lambda_powertools import Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from libs.common_tools import DecimalEncoder
from libs.utils import response_error

client = boto3.client('apigateway')

tracer = Tracer()

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

esd_version = os.environ.get("ESD_VERSION")


@dataclass
class Schema:
    type: str
    default: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self):
        data = {
            "type": self.type,
        }

        if self.default:
            data["default"] = self.default

        if self.description:
            data["description"] = self.description

        return data


@dataclass
class ExternalDocs:
    url: str
    description: str

    def to_dict(self):
        return {"url": self.url, "description": self.description}


@dataclass
class Tag:
    name: str
    description: str
    externalDocs: Optional[ExternalDocs] = None

    def to_dict(self):
        if self.externalDocs:
            return {"name": self.name, "description": self.description, "externalDocs": self.externalDocs.to_dict()}
        return {"name": self.name, "description": self.description}


@dataclass
class Parameter:
    name: str
    description: str
    location: str
    required: bool = False
    schema: Optional[Schema] = None

    def to_dict(self):
        if self.schema:
            return {
                "name": self.name,
                "description": self.description,
                "in": self.location,
                "required": self.required,
                "schema": self.schema.to_dict(),
            }

        return {
            "name": self.name,
            "description": self.description,
            "in": self.location,
            "required": self.required,
        }


@dataclass
class APISchema:
    summary: str
    tags: List[str]
    parameters: Optional[List[Parameter]] = field(default_factory=list)
    description: str = ""


header_user_name = Parameter(
    name="username",
    description="Username",
    location="header",
    required=True,
    schema=Schema(type="string", default="api")
)

path_id = Parameter(name="id", description="ID", location="path", required=True)
path_name = Parameter(name="name", description="Name", location="path", required=True)
path_dataset_name = Parameter(name="id", description="Dataset Name", location="path", required=True)

query_limit = Parameter(name="limit", description="Limit Per Page", location="query")
query_page = Parameter(name="page", description="Page Index", location="query")
query_per_page = Parameter(name="per_page", description="Limit Per Page", location="query")
query_exclusive_start_key = Parameter(name="exclusive_start_key", description="Exclusive Start Key", location="query")

tags = [
    Tag(name="Service", description="Service API").to_dict(),
    Tag(name="Roles", description="Manage Roles").to_dict(),
    Tag(name="Users", description="Manage Users").to_dict(),
    Tag(name="Endpoints", description="Manage Endpoints").to_dict(),
    Tag(
        name="Checkpoints",
        description="Manage Checkpoints",
        externalDocs=ExternalDocs(
            url="https://awslabs.github.io/stable-diffusion-aws-extension/en/developer-guide/api_upload_ckpt/",
            description="Upload Checkpoint Process")
    ).to_dict(),
    Tag(
        name="Inferences",
        description="Manage Inferences",
        externalDocs=ExternalDocs(
            url="https://awslabs.github.io/stable-diffusion-aws-extension/en/developer-guide/api_inference_process/",
            description="Inference Process")
    ).to_dict(),
    Tag(name="Executes", description="Manage Executes").to_dict(),
    Tag(name="Datasets", description="Manage Datasets").to_dict(),
    Tag(name="Trainings", description="Manage Trainings").to_dict(),
    Tag(name="Prepare", description="Sync files to Endpoint").to_dict(),
    Tag(name="Sync", description="Sync Message from Endpoint").to_dict(),
    Tag(name="Workflows", description="Manage Workflows").to_dict(),
    Tag(name="Schemas", description="Manage Schemas").to_dict(),
    Tag(name="Others", description="Others API").to_dict(),
]

operations = {
    "RootAPI": APISchema(
        summary="Root API",
        tags=["Service"],
        description="The Root API of ESD"
    ),
    "Ping": APISchema(
        summary="Ping API",
        tags=["Service"],
        description="The Ping API for Health Check"
    ),
    "ListRoles": APISchema(
        summary="List Roles",
        tags=["Roles"],
        description="List all roles",
        parameters=[
            header_user_name
        ]
    ),
    "GetInferenceJob": APISchema(
        summary="Get Inference Job",
        tags=["Inferences"],
        description="Get Inference Job",
        parameters=[
            header_user_name,
            path_id
        ]
    ),
    "CreateRole": APISchema(
        summary="Create Role",
        tags=["Roles"],
        description="Create a new role",
        parameters=[
            header_user_name
        ]
    ),
    "DeleteRoles": APISchema(
        summary="Delete Roles",
        tags=["Roles"],
        description="Delete specify Roles",
        parameters=[
            header_user_name
        ]
    ),
    "GetTraining": APISchema(
        summary="Get Training",
        tags=["Trainings"],
        description="Get Training List",
        parameters=[
            header_user_name,
            path_id
        ]
    ),
    "ListCheckpoints": APISchema(
        summary="List Checkpoints",
        tags=["Checkpoints"],
        description="List Checkpoints with Parameters",
        parameters=[
            header_user_name,
            query_page,
            query_per_page,
            Parameter(name="username", description="Filter by username", location="query"),
        ]
    ),
    "CreateCheckpoint": APISchema(
        summary="Create Checkpoint",
        tags=["Checkpoints"],
        description="Create a new Checkpoint",
        parameters=[
            header_user_name
        ]
    ),
    "DeleteCheckpoints": APISchema(
        summary="Delete Checkpoints",
        tags=["Checkpoints"],
        description="Delete specify Checkpoints",
        parameters=[
            header_user_name
        ]
    ),
    "StartInferences": APISchema(
        summary="Start Inference Job",
        tags=["Inferences"],
        description="Start specify Inference Job by ID",
        parameters=[
            header_user_name,
            path_id
        ]
    ),
    "ListExecutes": APISchema(
        summary="List Executes",
        tags=["Executes"],
        description="List Executes with Parameters",
        parameters=[
            header_user_name,
            query_limit,
            query_exclusive_start_key
        ]
    ),
    "CreateExecute": APISchema(
        summary="Create Execute",
        tags=["Executes"],
        description="Create a new Execute for Comfy",
        parameters=[
            header_user_name
        ]
    ),
    "DeleteExecutes": APISchema(
        summary="Delete Executes",
        tags=["Executes"],
        description="Delete specify Executes",
        parameters=[
            header_user_name
        ]
    ),
    "MergeExecute": APISchema(
        summary="Merge Executes",
        tags=["Executes"],
        description="Merge specify Executes",
        parameters=[
            header_user_name
        ]
    ),
    "GetApiOAS": APISchema(
        summary="Get OAS",
        description="Get OAS json schema",
        tags=["Service"],
    ),
    "ListUsers": APISchema(
        summary="List Users",
        tags=["Users"],
        description="List all users",
        parameters=[
            header_user_name
        ]
    ),
    "CreateUser": APISchema(
        summary="Create User",
        tags=["Users"],
        description="Create a new user",
        parameters=[
            header_user_name
        ]
    ),
    "DeleteUsers": APISchema(
        summary="Delete Users",
        tags=["Users"],
        description="Delete specify Users",
        parameters=[
            header_user_name
        ]
    ),
    "ListTrainings": APISchema(
        summary="List Trainings",
        tags=["Trainings"],
        description="List Trainings with Parameters",
        parameters=[
            header_user_name,
            query_limit,
            query_exclusive_start_key
        ]
    ),
    "CreateTraining": APISchema(
        summary="Create Training",
        tags=["Trainings"],
        description="Create a new Training Job",
        parameters=[
            header_user_name
        ]
    ),
    "DeleteTrainings": APISchema(
        summary="Delete Trainings",
        tags=["Trainings"],
        description="Delete specify Trainings",
        parameters=[
            header_user_name
        ]
    ),
    "GetExecute": APISchema(
        summary="Get Execute",
        tags=["Executes"],
        description="Get Execute by ID",
        parameters=[
            header_user_name,
            path_id
        ]
    ),
    "GetExecuteLogs": APISchema(
        summary="Get Execute Logs",
        tags=["Executes"],
        description="Get Execute Logs by ID",
        parameters=[
            header_user_name,
            path_id
        ]
    ),
    "ListDatasets": APISchema(
        summary="List Datasets",
        tags=["Datasets"],
        description="List Datasets with Parameters",
        parameters=[
            header_user_name,
            query_limit,
            query_exclusive_start_key
        ]
    ),
    "CropDataset": APISchema(
        summary="Create new Crop Dataset",
        tags=["Datasets"],
        description="Create new Crop Dataset",
        parameters=[
            header_user_name,
            path_dataset_name
        ]
    ),
    "GetDataset": APISchema(
        summary="Get Dataset",
        tags=["Datasets"],
        description="Get Dataset by ID",
        parameters=[
            header_user_name,
            path_dataset_name
        ]
    ),
    "UpdateCheckpoint": APISchema(
        summary="Update Checkpoint",
        tags=["Checkpoints"],
        description="Update Checkpoint by ID",
        parameters=[
            header_user_name,
            path_dataset_name
        ]
    ),
    "CreateDataset": APISchema(
        summary="Create Dataset",
        tags=["Datasets"],
        description="Create a new Dataset",
        parameters=[
            header_user_name
        ]
    ),
    "DeleteDatasets": APISchema(
        summary="Delete Datasets",
        tags=["Datasets"],
        description="Delete specify Datasets",
        parameters=[
            header_user_name
        ]
    ),
    "UpdateDataset": APISchema(
        summary="Update Dataset",
        tags=["Datasets"],
        description="Update Dataset by ID",
        parameters=[
            header_user_name,
            path_dataset_name
        ]
    ),
    "ListInferences": APISchema(
        summary="List Inferences",
        tags=["Inferences"],
        description="List Inferences with Parameters",
        parameters=[
            header_user_name,
            query_limit,
            query_exclusive_start_key,
            Parameter(name="type", description="Inference task type: txt2img, img2img", location="query"),
        ]
    ),
    "CreateInferenceJob": APISchema(
        summary="Create Inference Job",
        tags=["Inferences"],
        description="Create a new Inference Job",
        parameters=[
            header_user_name
        ]
    ),
    "DeleteInferenceJobs": APISchema(
        summary="Delete Inference Jobs",
        tags=["Inferences"],
        description="Delete specify Inference Jobs",
        parameters=[
            header_user_name
        ]
    ),
    "ListEndpoints": APISchema(
        summary="List Endpoints",
        tags=["Endpoints"],
        description="List Endpoints with Parameters",
        parameters=[
            header_user_name,
            query_limit,
            query_exclusive_start_key
        ]
    ),
    "CreateEndpoint": APISchema(
        summary="Create Endpoint",
        tags=["Endpoints"],
        description="Create a new Endpoint",
        parameters=[
            header_user_name
        ]
    ),
    "DeleteEndpoints": APISchema(
        summary="Delete Endpoints",
        tags=["Endpoints"],
        description="Delete specify Endpoints",
        parameters=[
            header_user_name
        ]
    ),
    "SyncMessage": APISchema(
        summary="Sync Message",
        tags=["Sync"],
        description="Sync Message to Endpoint",
        parameters=[
            header_user_name
        ]
    ),
    "GetSyncMessage": APISchema(
        summary="Get Sync Message",
        description="Get Sync Message from Endpoint",
        tags=["Sync"],
        parameters=[
            header_user_name
        ]
    ),
    "CreatePrepare": APISchema(
        summary="Create Prepare",
        tags=["Prepare"],
        description="Create a new Prepare",
        parameters=[
            header_user_name
        ]
    ),
    "GetPrepare": APISchema(
        summary="Get Prepare",
        tags=["Prepare"],
        description="Get Prepare by ID",
        parameters=[
            header_user_name
        ]
    ),
    "CreateWorkflow": APISchema(
        summary="Release new Workflow",
        tags=["Workflows"],
        description="Create a new Workflow",
    ),
    "ListWorkflows": APISchema(
        summary="List Workflows",
        tags=["Workflows"],
        description="List Workflows with Parameters",
    ),
    "DeleteWorkflows": APISchema(
        summary="Delete Workflows",
        tags=["Workflows"],
        description="Delete specify Workflows",
    ),
    'GetWorkflow': APISchema(
        summary="Get Workflow",
        tags=["Workflows"],
        description="Get Workflow by Name",
        parameters=[
            path_name
        ]
    ),
    "CreateSchema": APISchema(
        summary="Release new Schema",
        tags=["Schemas"],
        description="Create a new Schema",
    ),
    "ListSchemas": APISchema(
        summary="List Schemas",
        tags=["Schemas"],
        description="List Schemas with Parameters",
    ),
    "DeleteSchemas": APISchema(
        summary="Delete Schemas",
        tags=["Schemas"],
        description="Delete specify Schemas",
    ),
    'GetSchema': APISchema(
        summary="Get Schema",
        tags=["Schemas"],
        description="Get Schema by Name",
        parameters=[
            path_name
        ]
    ),
    'UpdateSchema': APISchema(
        summary="Update Schema",
        tags=["Schemas"],
        description="Update Schema by Name",
        parameters=[
            path_name
        ]
    ),
}


@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext):
    logger.info(f'event: {event}')
    logger.info(f'ctx: {context}')

    api_id = event['requestContext']['apiId']

    try:
        response = client.get_export(
            restApiId=api_id,
            stageName='prod',
            exportType='oas30',
            accepts='application/json',
            # parameters={
            #     'extensions': 'apigateway'
            # }
        )

        oas = response['body'].read()
        json_schema = json.loads(oas)
        json_schema = replace_null(json_schema)
        json_schema['info']['version'] = esd_version.split('-')[0]

        json_schema['servers'] = [
            {
                "url": "https://{ApiId}.execute-api.{Region}.{Domain}/prod/",
                "variables": {
                    "ApiId": {
                        "default": "xxxxxx"
                    },
                    "Region": {
                        "default": "ap-northeast-1"
                    },
                    "Domain": {
                        "default": "amazonaws.com"
                    },
                }
            }
        ]

        json_schema['info']['license'] = {
            "name": "Apache 2.0",
            "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
        }

        json_schema['info']['description'] = (
            "This is a ESD Server based on the OpenAPI 3.0 specification. \n"
            "Some useful links: \n"
            "\n- [The ESD Repository](https://github.com/awslabs/stable-diffusion-aws-extension)"
            "\n- [Implementation Guide](https://awslabs.github.io/stable-diffusion-aws-extension/en/)")

        json_schema['tags'] = tags

        for path in json_schema['paths']:
            for method in json_schema['paths'][path]:
                meta = supplement_schema(json_schema['paths'][path][method])
                json_schema['paths'][path][method]['description'] = meta.description
                json_schema['paths'][path][method]['summary'] = meta.summary
                json_schema['paths'][path][method]['tags'] = meta.tags
                json_schema['paths'][path][method]['parameters'] = merge_parameters(meta,
                                                                                    json_schema['paths'][path][method])

        json_schema['paths'] = dict(sorted(json_schema['paths'].items(), key=lambda x: x[0]))

        payload = {
            'isBase64Encoded': False,
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Methods': '*',
                'Access-Control-Allow-Credentials': True,
            },
            'body': json.dumps(json_schema, cls=DecimalEncoder, indent=2)
        }

        return payload
    except Exception as e:
        return response_error(e)


def merge_parameters(schema: APISchema, item: dict):
    if not schema.parameters:
        return []

    if 'parameters' not in item or len(item['parameters']) == 0:
        item['parameters'] = []
        for param in schema.parameters:
            item['parameters'].append(param.to_dict())
        return item['parameters']

    for param in schema.parameters:

        update = False
        for original_para in item['parameters']:
            if param.name == original_para['name'] and param.location == original_para['in']:
                update = True
                original_para.update(param.to_dict())

        if update is False:
            item['parameters'].append(param.to_dict())

    return item['parameters']


def replace_null(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if value is None:
                data[key] = {
                    "type": "null",
                    "description": "Last Key for Pagination"
                }
            else:
                data[key] = replace_null(value)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if item is None:
                data[i] = {
                    "type": "null",
                    "description": "Last Key for Pagination"
                }
            else:
                data[i] = replace_null(item)

    return data


def supplement_schema(method: any):
    if 'operationId' in method:
        if method['operationId'] in operations:
            item: APISchema = operations[method['operationId']]
            if item.parameters:
                parameters = item.parameters
            else:
                parameters = []

            return APISchema(
                summary=item.summary + f" ({method['operationId']})",
                tags=item.tags,
                description=item.description,
                parameters=parameters
            )

        return APISchema(
            summary=method['operationId'],
            tags=["Others"],
            parameters=[]
        )

    return APISchema(
        summary="",
        tags=["Others"],
        parameters=[]
    )
