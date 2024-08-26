import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_apigateway, aws_dynamodb, aws_iam, aws_lambda, aws_s3, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model } from 'aws-cdk-lib/aws-apigateway';
import { Effect, PolicyStatement } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Size } from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import {
  SCHEMA_DEBUG,
  SCHEMA_INFER_TYPE,
  SCHEMA_INFERENCE,
  SCHEMA_INFERENCE_ASYNC_MODEL,
  SCHEMA_INFERENCE_REAL_TIME_MODEL,
  SCHEMA_MESSAGE, SCHEMA_WORKFLOW,
} from '../../shared/schema';
import { ApiValidators } from '../../shared/validator';

export interface CreateInferenceJobApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  endpointDeploymentTable: aws_dynamodb.Table;
  inferenceJobTable: aws_dynamodb.Table;
  s3Bucket: aws_s3.Bucket;
  commonLayer: aws_lambda.LayerVersion;
  checkpointTable: aws_dynamodb.Table;
  multiUserTable: aws_dynamodb.Table;
}

export class CreateInferenceJobApi {

  private readonly id: string;
  private readonly scope: Construct;
  private readonly endpointDeploymentTable: aws_dynamodb.Table;
  private readonly inferenceJobTable: aws_dynamodb.Table;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly s3Bucket: aws_s3.Bucket;
  private readonly httpMethod: string;
  private readonly router: aws_apigateway.Resource;
  private readonly checkpointTable: aws_dynamodb.Table;
  private readonly multiUserTable: aws_dynamodb.Table;

  constructor(scope: Construct, id: string, props: CreateInferenceJobApiProps) {
    this.id = id;
    this.scope = scope;
    this.checkpointTable = props.checkpointTable;
    this.multiUserTable = props.multiUserTable;
    this.endpointDeploymentTable = props.endpointDeploymentTable;
    this.inferenceJobTable = props.inferenceJobTable;
    this.layer = props.commonLayer;
    this.s3Bucket = props.s3Bucket;
    this.httpMethod = props.httpMethod;
    this.router = props.router;

    const lambdaFunction = this.apiLambda();

    const lambdaIntegration = new LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.addMethod(this.httpMethod, lambdaIntegration, {
      apiKeyRequired: true,
      requestValidator: ApiValidators.bodyValidator,
      requestModels: {
        'application/json': this.createRequestBodyModel(),
      },
      operationName: 'CreateInferenceJob',
      methodResponses: [
        ApiModels.methodResponse(this.responseRealtimeModel(), '200'),
        ApiModels.methodResponse(this.responseCreatedModel(), '201'),
        ApiModels.methodResponse(this.responseAsyncModel(), '202'),
        ApiModels.methodResponses400(),
        ApiModels.methodResponses401(),
        ApiModels.methodResponses403(),
        ApiModels.methodResponses504(),
      ],
    });
  }

  private responseRealtimeModel() {
    return new Model(this.scope, `${this.id}-rt-resp-model`, {
      restApi: this.router.api,
      modelName: 'CreateInferenceJobRealtimeResponse',
      description: 'Response Model CreateInferenceJobRealtimeResponse',
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        title: 'CreateInferenceJobRealtimeResponse',
        type: JsonSchemaType.OBJECT,
        properties: SCHEMA_INFERENCE_REAL_TIME_MODEL,
        required: [
          'statusCode',
          'debug',
          'data',
          'message',
        ],
      },
      contentType: 'application/json',
    });
  }

  private responseAsyncModel() {
    return new Model(this.scope, `${this.id}-async-resp-model`, {
      restApi: this.router.api,
      modelName: 'CreateInferenceJobAsyncResponse',
      description: 'Response Model CreateInferenceJobAsyncResponse',
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        title: 'CreateInferenceJobAsyncResponse',
        type: JsonSchemaType.OBJECT,
        properties: SCHEMA_INFERENCE_ASYNC_MODEL,
        required: [
          'statusCode',
          'debug',
          'data',
          'message',
        ],
      },
      contentType: 'application/json',
    });
  }

  private responseCreatedModel() {
    return new Model(this.scope, `${this.id}-resp-model`, {
      restApi: this.router.api,
      modelName: 'CreateInferenceJobResponse',
      description: 'Response Model CreateInferenceJob',
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        title: 'CreateInferenceJobResponse',
        type: JsonSchemaType.OBJECT,
        properties: {
          statusCode: {
            type: JsonSchemaType.NUMBER,
          },
          debug: SCHEMA_DEBUG,
          message: SCHEMA_MESSAGE,
          data: {
            type: JsonSchemaType.OBJECT,
            properties: {
              inference: {
                type: JsonSchemaType.OBJECT,
                additionalProperties: true,
                properties: {
                  id: SCHEMA_INFERENCE.InferenceJobId,
                  type: {
                    type: JsonSchemaType.STRING,
                  },
                  workflow: SCHEMA_WORKFLOW,
                  api_params_s3_location: {
                    type: JsonSchemaType.STRING,
                    format: 'uri',
                  },
                  api_params_s3_upload_url: {
                    type: JsonSchemaType.STRING,
                    format: 'uri',
                  },
                  models: {
                    type: JsonSchemaType.ARRAY,
                    items: {
                      type: JsonSchemaType.OBJECT,
                      properties: {
                        id: {
                          type: JsonSchemaType.STRING,
                          format: 'uuid',
                        },
                        name: {
                          type: JsonSchemaType.ARRAY,
                          items: {
                            type: JsonSchemaType.STRING,
                          },
                        },
                        type: {
                          type: JsonSchemaType.STRING,
                        },
                      },
                      required: [
                        'id',
                        'name',
                        'type',
                      ],
                    },
                  },
                },
                required: [
                  'id',
                  'type',
                  'api_params_s3_location',
                  'api_params_s3_upload_url',
                ],
              },
            },
            required: [
              'inference',
            ],
          },
        },
        required: [
          'statusCode',
          'debug',
          'data',
          'message',
        ],
      },
      contentType: 'application/json',
    });
  }

  private createRequestBodyModel(): Model {
    return new Model(this.scope, `${this.id}-model`, {
      restApi: this.router.api,
      modelName: `${this.id}Request`,
      description: `Request Model ${this.id}`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        title: this.id,
        type: JsonSchemaType.OBJECT,
        properties: {
          task_type: {
            type: JsonSchemaType.STRING,
            minLength: 1,
          },
          custom_extensions: {
            type: JsonSchemaType.STRING,
          },
          inference_type: SCHEMA_INFER_TYPE,
          workflow: SCHEMA_WORKFLOW,
          payload_string: {
            type: JsonSchemaType.STRING,
          },
          models: {
            type: JsonSchemaType.OBJECT,
            properties: {
              embeddings: {
                type: JsonSchemaType.ARRAY,
              },
            },
          },
        },
        required: [
          'task_type',
          'inference_type',
          'models',
        ],
      },
      contentType: 'application/json',
    });
  }

  private lambdaRole(): aws_iam.Role {
    const newRole = new aws_iam.Role(this.scope, `${this.id}-role`, {
      assumedBy: new aws_iam.ServicePrincipal('lambda.amazonaws.com'),
    });

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'dynamodb:BatchGetItem',
        'dynamodb:GetItem',
        'dynamodb:Scan',
        'dynamodb:Query',
        'dynamodb:BatchWriteItem',
        'dynamodb:PutItem',
        'dynamodb:UpdateItem',
        'dynamodb:DeleteItem',
      ],
      resources: [
        this.inferenceJobTable.tableArn,
        this.endpointDeploymentTable.tableArn,
        this.checkpointTable.tableArn,
        this.multiUserTable.tableArn,
      ],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'sagemaker:InvokeEndpointAsync',
        'sagemaker:InvokeEndpoint',
      ],
      resources: [`arn:${Aws.PARTITION}:sagemaker:${Aws.REGION}:${Aws.ACCOUNT_ID}:endpoint/*`],
    }));

    newRole.addToPolicy(new PolicyStatement({
      actions: [
        's3:PutObject',
      ],
      resources: [
        `${this.s3Bucket.bucketArn}/*`,
        `arn:${Aws.PARTITION}:s3:::*SageMaker*`,
      ],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        's3:GetObject',
        's3:PutObject',
        's3:DeleteObject',
        's3:ListBucket',
      ],
      resources: [`${this.s3Bucket.bucketArn}/*`,
        `arn:${Aws.PARTITION}:s3:::*sagemaker*`],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'logs:CreateLogGroup',
        'logs:CreateLogStream',
        'logs:PutLogEvents',
        'cloudwatch:PutMetricAlarm',
        'cloudwatch:PutMetricData',
        'kms:Decrypt',
      ],
      resources: ['*'],
    }));

    return newRole;
  }

  private apiLambda() {
    return new PythonFunction(this.scope, `${this.id}-lambda`, {
      entry: '../middleware_api/inferences',
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'create_inference_job.py',
      handler: 'handler',
      memorySize: 3000,
      tracing: aws_lambda.Tracing.ACTIVE,
      ephemeralStorageSize: Size.gibibytes(10),
      timeout: Duration.seconds(900),
      role: this.lambdaRole(),
      environment: {
        INFERENCE_JOB_TABLE: this.inferenceJobTable.tableName,
        CHECKPOINT_TABLE: this.checkpointTable.tableName,
      },
      layers: [this.layer],
    });
  }

}
