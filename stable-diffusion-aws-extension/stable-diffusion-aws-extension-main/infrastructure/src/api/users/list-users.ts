import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import {Aws, aws_apigateway, aws_dynamodb, aws_kms, aws_lambda, Duration} from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model } from 'aws-cdk-lib/aws-apigateway';
import {Role} from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import {
  SCHEMA_CREATOR,
  SCHEMA_DEBUG,
  SCHEMA_LAST_KEY,
  SCHEMA_MESSAGE, SCHEMA_PASSWORD,
  SCHEMA_PERMISSIONS,
  SCHEMA_USER_ROLES,
  SCHEMA_USERNAME,
} from '../../shared/schema';
import {ESD_ROLE} from "../../shared/const";


export interface ListUsersApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  multiUserTable: aws_dynamodb.Table;
  commonLayer: aws_lambda.LayerVersion;
  passwordKey: aws_kms.IKey;
}

export class ListUsersApi {
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly passwordKey: aws_kms.IKey;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: ListUsersApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.passwordKey = props.passwordKey;
    this.httpMethod = props.httpMethod;
    this.layer = props.commonLayer;

    const lambdaFunction = this.apiLambda();

    const integration = new LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.addMethod(this.httpMethod, integration, {
      apiKeyRequired: true,
      operationName: 'ListUsers',
      methodResponses: [
        ApiModels.methodResponse(this.responseModel()),
        ApiModels.methodResponses400(),
        ApiModels.methodResponses401(),
        ApiModels.methodResponses403(),
        ApiModels.methodResponses404(),
      ],
    });
  }

  private responseModel() {
    return new Model(this.scope, `${this.baseId}-resp-model`, {
      restApi: this.router.api,
      modelName: 'ListUsersResponse',
      description: 'Response Model ListUsersResponse',
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        title: this.baseId,
        type: JsonSchemaType.OBJECT,
        properties: {
          statusCode: {
            type: JsonSchemaType.INTEGER,
            enum: [200],
          },
          debug: SCHEMA_DEBUG,
          message: SCHEMA_MESSAGE,
          data: {
            type: JsonSchemaType.OBJECT,
            properties: {
              users: {
                type: JsonSchemaType.ARRAY,
                items: {
                  type: JsonSchemaType.OBJECT,
                  properties: {
                    username: SCHEMA_USERNAME,
                    roles: SCHEMA_USER_ROLES,
                    creator: SCHEMA_CREATOR,
                    permissions: SCHEMA_PERMISSIONS,
                    password: SCHEMA_PASSWORD,
                  },
                  required: [
                    'creator',
                    'password',
                    'permissions',
                    'roles',
                    'username',
                  ],
                },
              },
              last_evaluated_key: SCHEMA_LAST_KEY,
            },
            required: [
              'users',
              'last_evaluated_key',
            ],
          },
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
    const role = <Role>Role.fromRoleName(this.scope, `${this.baseId}-role`, `${ESD_ROLE}-${Aws.REGION}`);

    return new PythonFunction(this.scope, `${this.baseId}-lambda`, {
      entry: '../middleware_api/users',
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'list_users.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: role,
      memorySize: 2048,
      tracing: aws_lambda.Tracing.ACTIVE,
      environment: {
        KEY_ID: `alias/${this.passwordKey.keyId}`,
      },
      layers: [this.layer],
    });
  }

}

