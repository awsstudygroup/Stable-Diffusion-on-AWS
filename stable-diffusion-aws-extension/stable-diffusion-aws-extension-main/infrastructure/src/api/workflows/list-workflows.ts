import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import {Aws, aws_apigateway, aws_dynamodb, aws_lambda, Duration} from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model } from 'aws-cdk-lib/aws-apigateway';
import {Role} from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import {
  SCHEMA_DEBUG,
  SCHEMA_LAST_KEY,
  SCHEMA_MESSAGE, SCHEMA_WORKFLOW_IMAGE_URI,
  SCHEMA_WORKFLOW_NAME, SCHEMA_WORKFLOW_PAYLOAD_JSON, SCHEMA_WORKFLOW_SIZE, SCHEMA_WORKFLOW_STATUS,
} from '../../shared/schema';
import {ESD_ROLE} from "../../shared/const";


export interface ListWorkflowsApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  workflowsTable: aws_dynamodb.Table;
  commonLayer: aws_lambda.LayerVersion;
}

export class ListWorkflowsApi {
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly workflowsTable: aws_dynamodb.Table;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly baseId: string;


  constructor(scope: Construct, id: string, props: ListWorkflowsApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.workflowsTable = props.workflowsTable;
    this.layer = props.commonLayer;

    const lambdaFunction = this.apiLambda();

    const lambdaIntegration = new LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.addMethod(this.httpMethod, lambdaIntegration, {
      apiKeyRequired: true,
      operationName: 'ListWorkflows',
      requestParameters: {
        'method.request.querystring.limit': false,
        'method.request.querystring.exclusive_start_key': false,
      },
      methodResponses: [
        ApiModels.methodResponse(this.responseModel()),
        ApiModels.methodResponses400(),
        ApiModels.methodResponses401(),
        ApiModels.methodResponses403(),
      ],
    });
  }

  private responseModel() {
    return new Model(this.scope, `${this.baseId}-resp-model`, {
      restApi: this.router.api,
      modelName: 'ListWorkflowsResponse',
      description: `Response Model ${this.baseId}`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        type: JsonSchemaType.OBJECT,
        title: 'ListWorkflowsResponse',
        properties: {
          statusCode: {
            type: JsonSchemaType.INTEGER,
            enum: [200],
          },
          debug: SCHEMA_DEBUG,
          message: SCHEMA_MESSAGE,
          data: {
            type: JsonSchemaType.OBJECT,
            additionalProperties: true,
            properties: {
              workflows: {
                type: JsonSchemaType.ARRAY,
                items: {
                  type: JsonSchemaType.OBJECT,
                  properties: {
                    name: SCHEMA_WORKFLOW_NAME,
                    size: SCHEMA_WORKFLOW_SIZE,
                    status: SCHEMA_WORKFLOW_STATUS,
                    image_uri: SCHEMA_WORKFLOW_IMAGE_URI,
                    payload_json: SCHEMA_WORKFLOW_PAYLOAD_JSON,
                  },
                  required: [
                    'name',
                    'size',
                    'status',
                    'image_uri',
                    'payload_json',
                  ],
                },
              },
              last_evaluated_key: SCHEMA_LAST_KEY,
            },
            required: [
              'workflows',
              'last_evaluated_key',
            ],
          },
        },
        required: [
          'statusCode',
          'debug',
          'data',
          'message',
        ],
      }
      ,
      contentType: 'application/json',
    });
  }

  private apiLambda() {
    const role = <Role>Role.fromRoleName(this.scope, `${this.baseId}-role`, `${ESD_ROLE}-${Aws.REGION}`);

    return new PythonFunction(this.scope, `${this.baseId}-lambda`, {
      entry: '../middleware_api/workflows',
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'list_workflows.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: role,
      memorySize: 2048,
      tracing: aws_lambda.Tracing.ACTIVE,
      layers: [this.layer],
      environment: {
        WORKFLOWS_TABLE: this.workflowsTable.tableName,
      }
    });
  }

}

