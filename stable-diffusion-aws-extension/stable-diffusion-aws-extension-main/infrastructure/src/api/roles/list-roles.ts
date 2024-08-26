import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import {Aws, aws_apigateway, aws_lambda, Duration} from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model } from 'aws-cdk-lib/aws-apigateway';
import {Role} from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import { SCHEMA_CREATOR, SCHEMA_DEBUG, SCHEMA_LAST_KEY, SCHEMA_MESSAGE, SCHEMA_PERMISSIONS } from '../../shared/schema';
import {ESD_ROLE} from "../../shared/const";


export interface ListAllRolesApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  commonLayer: aws_lambda.LayerVersion;
}

export class ListRolesApi {
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: ListAllRolesApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
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
      operationName: 'ListRoles',
      methodResponses: [
        ApiModels.methodResponse(this.responseModel()),
        ApiModels.methodResponses401(),
        ApiModels.methodResponses403(),
        ApiModels.methodResponses404(),
      ],
    });
  }

  private responseModel() {
    return new Model(this.scope, `${this.baseId}-resp-model`, {
      restApi: this.router.api,
      modelName: 'ListRolesResponse',
      description: 'Response Model ListRolesResponse',
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
              roles: {
                type: JsonSchemaType.ARRAY,
                items: {
                  type: JsonSchemaType.OBJECT,
                  properties: {
                    role_name: {
                      type: JsonSchemaType.STRING,
                    },
                    creator: SCHEMA_CREATOR,
                    permissions: SCHEMA_PERMISSIONS,
                  },
                  required: [
                    'role_name',
                    'creator',
                    'permissions',
                  ],
                },
              },
              last_evaluated_key: SCHEMA_LAST_KEY,
            },
            required: [
              'roles',
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
      },
      contentType: 'application/json',
    });
  }

  private apiLambda() {
    const role = <Role>Role.fromRoleName(this.scope, `${this.baseId}-role`, `${ESD_ROLE}-${Aws.REGION}`);

    return new PythonFunction(this.scope, `${this.baseId}-lambda`, {
      entry: '../middleware_api/roles',
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'list_roles.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: role,
      memorySize: 2048,
      tracing: aws_lambda.Tracing.ACTIVE,
      layers: [this.layer],
    });
  }


}

