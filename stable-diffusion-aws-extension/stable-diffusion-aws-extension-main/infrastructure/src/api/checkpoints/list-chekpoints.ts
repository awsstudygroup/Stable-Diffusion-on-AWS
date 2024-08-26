import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { aws_apigateway, aws_dynamodb, aws_iam, aws_lambda, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, Model } from 'aws-cdk-lib/aws-apigateway';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import { SCHEMA_CHECKPOINT_ID, SCHEMA_CHECKPOINT_STATUS, SCHEMA_CHECKPOINT_TYPE, SCHEMA_DEBUG, SCHEMA_MESSAGE } from '../../shared/schema';


export interface ListCheckPointsApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  checkpointTable: aws_dynamodb.Table;
  multiUserTable: aws_dynamodb.Table;
  commonLayer: aws_lambda.LayerVersion;
}

export class ListCheckPointsApi {
  public lambdaIntegration: aws_apigateway.LambdaIntegration;
  public router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly checkpointTable: aws_dynamodb.Table;
  private readonly multiUserTable: aws_dynamodb.Table;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: ListCheckPointsApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.checkpointTable = props.checkpointTable;
    this.multiUserTable = props.multiUserTable;
    this.layer = props.commonLayer;

    const lambdaFunction = this.apiLambda();

    this.lambdaIntegration = new aws_apigateway.LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.addMethod(this.httpMethod, this.lambdaIntegration, {
      apiKeyRequired: true,
      operationName: 'ListCheckpoints',
      requestParameters: {
        'method.request.querystring.page': false,
        'method.request.querystring.per_page': false,
        'method.request.querystring.username': false,
      },
      methodResponses: [
        ApiModels.methodResponse(this.responseModel(), '200'),
        ApiModels.methodResponses401(),
        ApiModels.methodResponses403(),
        ApiModels.methodResponses504(),
      ],
    });
  }

  private responseModel() {
    return new Model(this.scope, `${this.baseId}-resp-model`, {
      restApi: this.router.api,
      modelName: 'ListCheckpointsResponse',
      description: `Response Model ${this.baseId}`,
      schema: {
        title: 'ListCheckpointsResponse',
        schema: JsonSchemaVersion.DRAFT7,
        type: JsonSchemaType.OBJECT,
        properties: {
          statusCode: {
            type: JsonSchemaType.INTEGER,
          },
          debug: SCHEMA_DEBUG,
          message: SCHEMA_MESSAGE,
          data: {
            type: JsonSchemaType.OBJECT,
            properties: {
              page: {
                type: JsonSchemaType.INTEGER,
              },
              per_page: {
                type: JsonSchemaType.INTEGER,
              },
              pages: {
                type: JsonSchemaType.INTEGER,
              },
              total: {
                type: JsonSchemaType.INTEGER,
              },
              checkpoints: {
                type: JsonSchemaType.ARRAY,
                items: {
                  type: JsonSchemaType.OBJECT,
                  properties: {
                    id: SCHEMA_CHECKPOINT_ID,
                    s3Location: {
                      type: JsonSchemaType.STRING,
                    },
                    type: SCHEMA_CHECKPOINT_TYPE,
                    status: SCHEMA_CHECKPOINT_STATUS,
                    name: {
                      type: JsonSchemaType.ARRAY,
                      items: {
                        type: JsonSchemaType.STRING,
                      },
                    },
                    created: {
                      type: JsonSchemaType.STRING,
                    },
                    allowed_roles_or_users: {
                      type: JsonSchemaType.ARRAY,
                      items: {
                        type: JsonSchemaType.STRING,
                      },
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
                  },
                  required: [
                    'allowed_roles_or_users',
                    'created',
                    'id',
                    'name',
                    's3Location',
                    'status',
                    'type',
                  ],
                },
              },
            },
            required: [
              'checkpoints',
              'page',
              'pages',
              'per_page',
              'total',
            ],
          },
        },
        required: [
          'data',
          'debug',
          'message',
          'statusCode',
        ],
      }
      ,
      contentType: 'application/json',
    });
  }

  private apiLambda() {
    return new PythonFunction(this.scope, `${this.baseId}-lambda`, {
      entry: '../middleware_api/checkpoints',
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'list_checkpoints.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.iamRole(),
      memorySize: 2048,
      tracing: aws_lambda.Tracing.ACTIVE,
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
      ],
      resources: [this.checkpointTable.tableArn, this.multiUserTable.tableArn],
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

    return newRole;
  }

}
