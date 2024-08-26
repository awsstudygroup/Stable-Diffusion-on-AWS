import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_apigateway, aws_dynamodb, aws_iam, aws_lambda, aws_s3, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model } from 'aws-cdk-lib/aws-apigateway';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Size } from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import { SCHEMA_CHECKPOINT_ID, SCHEMA_CHECKPOINT_STATUS, SCHEMA_CHECKPOINT_TYPE, SCHEMA_DEBUG, SCHEMA_MESSAGE } from '../../shared/schema';
import { ApiValidators } from '../../shared/validator';


export interface CreateCheckPointApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  checkpointTable: aws_dynamodb.Table;
  multiUserTable: aws_dynamodb.Table;
  commonLayer: aws_lambda.LayerVersion;
  s3Bucket: aws_s3.Bucket;
}

export class CreateCheckPointApi {
  public lambdaIntegration: aws_apigateway.LambdaIntegration;
  public router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly checkpointTable: aws_dynamodb.Table;
  private readonly multiUserTable: aws_dynamodb.Table;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly s3Bucket: aws_s3.Bucket;
  private readonly uploadByUrlLambda: PythonFunction;
  private readonly role: aws_iam.Role;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: CreateCheckPointApiProps) {
    this.scope = scope;
    this.httpMethod = props.httpMethod;
    this.checkpointTable = props.checkpointTable;
    this.multiUserTable = props.multiUserTable;
    this.baseId = id;
    this.router = props.router;
    this.layer = props.commonLayer;
    this.s3Bucket = props.s3Bucket;
    this.role = this.iamRole();
    this.uploadByUrlLambda = this.uploadByUrlLambdaFunction();

    const lambdaFunction = this.apiLambda();

    this.lambdaIntegration = new LambdaIntegration(lambdaFunction, { proxy: true });

    this.router.addMethod(this.httpMethod, this.lambdaIntegration, {
      apiKeyRequired: true,
      requestValidator: ApiValidators.bodyValidator,
      requestModels: {
        'application/json': this.createRequestBodyModel(),
      },
      operationName: 'CreateCheckpoint',
      methodResponses: [
        ApiModels.methodResponse(this.responseModel(), '201'),
        ApiModels.methodResponse(this.responseUrlModel(), '202'),
        ApiModels.methodResponses400(),
        ApiModels.methodResponses401(),
        ApiModels.methodResponses403(),
        ApiModels.methodResponses504(),
      ],
    });
  }

  private responseUrlModel() {
    return new Model(this.scope, `${this.baseId}-url-model`, {
      restApi: this.router.api,
      modelName: 'CreateCheckpointUrlResponse',
      description: `Response Model ${this.baseId}`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        type: JsonSchemaType.OBJECT,
        properties: {
          statusCode: {
            type: JsonSchemaType.INTEGER,
          },
          debug: SCHEMA_DEBUG,
          message: SCHEMA_MESSAGE,
        },
        required: [
          'debug',
          'message',
          'statusCode',
        ],
      },
      contentType: 'application/json',
    });
  }

  private responseModel() {
    return new Model(this.scope, `${this.baseId}-update-model`, {
      restApi: this.router.api,
      modelName: 'CreateCheckpointResponse',
      description: `Response Model ${this.baseId}`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        type: JsonSchemaType.OBJECT,
        title: 'CreateCheckpointResponse',
        properties: {
          statusCode: {
            type: JsonSchemaType.INTEGER,
          },
          debug: SCHEMA_DEBUG,
          data: {
            type: JsonSchemaType.OBJECT,
            properties: {
              checkpoint: {
                type: JsonSchemaType.OBJECT,
                additionalProperties: true,
                properties: {
                  id: SCHEMA_CHECKPOINT_ID,
                  type: SCHEMA_CHECKPOINT_TYPE,
                  s3_location: {
                    type: JsonSchemaType.STRING,
                    description: 'S3 location of the checkpoint',
                  },
                  status: SCHEMA_CHECKPOINT_STATUS,
                  params: {
                    type: JsonSchemaType.OBJECT,
                    additionalProperties: true,
                    properties: {
                      message: {
                        type: JsonSchemaType.STRING,
                      },
                      creator: {
                        type: JsonSchemaType.STRING,
                      },
                      created: {
                        type: JsonSchemaType.STRING,
                      },
                      multipart_upload: {
                        type: JsonSchemaType.OBJECT,
                        properties: {
                          '.*': {
                            type: JsonSchemaType.OBJECT,
                            properties: {
                              upload_id: {
                                type: JsonSchemaType.STRING,
                              },
                              bucket: {
                                type: JsonSchemaType.STRING,
                              },
                              key: {
                                type: JsonSchemaType.STRING,
                              },
                            },
                            required: [
                              'bucket',
                              'key',
                              'upload_id',
                            ],
                          },
                        },
                      },
                    },
                    required: [
                      'created',
                      'creator',
                      'message',
                      'multipart_upload',
                    ],
                  },
                  source_path: {
                    oneOf: [
                      {
                        type: JsonSchemaType.NULL,
                      },
                      {
                        type: JsonSchemaType.STRING,
                      },
                    ],
                  },
                  target_path: {
                    oneOf: [
                      {
                        type: JsonSchemaType.NULL,
                      },
                      {
                        type: JsonSchemaType.STRING,
                      },
                    ],
                  },
                },
                required: [
                  'id',
                  'params',
                  's3_location',
                  'status',
                  'type',
                ],
              },
              s3PresignUrl: {
                type: JsonSchemaType.OBJECT,
                properties: {
                  '.*': {
                    type: JsonSchemaType.ARRAY,
                    items: {
                      type: JsonSchemaType.STRING,
                    },
                  },
                },
              },
            },
            required: [
              'checkpoint',
              's3PresignUrl',
            ],
          },
          message: SCHEMA_MESSAGE,
        },
        required: [
          'data',
          'debug',
          'message',
          'statusCode',
        ],
      },
      contentType: 'application/json',
    });
  }

  private apiLambda() {
    return new PythonFunction(this.scope, `${this.baseId}-lambda`, {
      entry: '../middleware_api/checkpoints',
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'create_checkpoint.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.role,
      memorySize: 3000,
      tracing: aws_lambda.Tracing.ACTIVE,
      environment: {
        CHECKPOINT_TABLE: this.checkpointTable.tableName,
        UPLOAD_BY_URL_LAMBDA_NAME: this.uploadByUrlLambda.functionName,
      },
      layers: [this.layer],
    });
  }

  private uploadByUrlLambdaFunction() {
    return new PythonFunction(this.scope, `${this.baseId}-url-lambda`, {
      functionName: `${this.baseId}-create-checkpoint-by-url`,
      entry: '../middleware_api/checkpoints',
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'update_checkpoint_by_url.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.role,
      memorySize: 3000,
      tracing: aws_lambda.Tracing.ACTIVE,
      ephemeralStorageSize: Size.mebibytes(10240),
      environment: {
        CHECKPOINT_TABLE: this.checkpointTable.tableName,
      },
      layers: [this.layer],
    });
  }

  private iamRole(): aws_iam.Role {
    const newRole = new aws_iam.Role(this.scope, `${this.baseId}-role`, {
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
      resources: [this.checkpointTable.tableArn, this.multiUserTable.tableArn],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        's3:GetObject',
        's3:PutObject',
        's3:DeleteObject',
        's3:ListBucket',
        's3:AbortMultipartUpload',
        's3:ListMultipartUploadParts',
        's3:ListBucketMultipartUploads',
      ],
      resources: [
        `${this.s3Bucket.bucketArn}/*`,
        `arn:${Aws.PARTITION}:s3:::*SageMaker*`,
      ],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'logs:CreateLogGroup',
        'logs:CreateLogStream',
        'logs:PutLogEvents',
        'kms:Decrypt',
      ],
      resources: ['*'],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'lambda:invokeFunction',
      ],
      resources: [
        `arn:${Aws.PARTITION}:lambda:${Aws.REGION}:${Aws.ACCOUNT_ID}:function:*${this.baseId}*`,
      ],
    }));

    return newRole;
  }

  private createRequestBodyModel(): Model {
    return new Model(this.scope, `${this.baseId}-model`, {
      restApi: this.router.api,
      modelName: `${this.baseId}Request`,
      description: `Request Model ${this.baseId}`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        title: this.baseId,
        type: JsonSchemaType.OBJECT,
        properties: {
          checkpoint_type: SCHEMA_CHECKPOINT_TYPE,
          filenames: {
            type: JsonSchemaType.ARRAY,
            items: {
              type: JsonSchemaType.OBJECT,
              properties: {
                filename: {
                  type: JsonSchemaType.STRING,
                  minLength: 1,
                },
                parts_number: {
                  type: JsonSchemaType.INTEGER,
                  minimum: 1,
                  maximum: 100,
                },
              },
            },
            minItems: 1,
            maxItems: 20,
          },
          urls: {
            type: JsonSchemaType.ARRAY,
            items: {
              type: JsonSchemaType.STRING,
              minLength: 1,
            },
            minItems: 1,
            maxItems: 20,
          },
          params: {
            type: JsonSchemaType.OBJECT,
            properties: {
              message: {
                type: JsonSchemaType.STRING,
              },
            },
          },
          target_path: {
            type: JsonSchemaType.STRING,
          },
          source_path: {
            type: JsonSchemaType.STRING,
          },
        },
        required: [
          'checkpoint_type',
        ],
      },
      contentType: 'application/json',
    });
  }

}

