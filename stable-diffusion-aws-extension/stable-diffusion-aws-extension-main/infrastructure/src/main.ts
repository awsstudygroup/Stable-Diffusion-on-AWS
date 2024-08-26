import { App, Aspects, Aws, aws_apigateway, CfnCondition, CfnOutput, CfnParameter, Fn, Stack, StackProps, Tags } from 'aws-cdk-lib';
import { Function } from 'aws-cdk-lib/aws-lambda';
import { Bucket } from 'aws-cdk-lib/aws-s3';
import { BootstraplessStackSynthesizer, CompositeECRRepositoryAspect } from 'cdk-bootstrapless-synthesizer';
import { Construct } from 'constructs';
import { OasApi } from './api/service/oas';
import { PingApi } from './api/service/ping';
import { RootAPI } from './api/service/root';
import { CheckpointStack } from './checkpoints/checkpoint-stack';
import { ComfyApiStack, ComfyInferenceStackProps } from './comfy/comfy-api-stack';
import { ComfyDatabase } from './comfy/comfy-database';
import { SqsStack } from './comfy/comfy-sqs';
import { EndpointStack } from './endpoints/endpoint-stack';
import { ESD_COMMIT_ID } from './shared/commit';
import { LambdaCommonLayer } from './shared/common-layer';
import { STACK_ID } from './shared/const';
import { Database } from './shared/database';
import { DatasetStack } from './shared/dataset';
import { Inference } from './shared/inference';
import { MultiUsers } from './shared/multi-users';
import { ResourceProvider } from './shared/resource-provider';
import { ResourceWaiter } from './shared/resource-waiter';
import { RestApiGateway } from './shared/rest-api-gateway';
import { SnsTopics } from './shared/sns-topics';
import { TrainDeploy } from './shared/train-deploy';
import { ESD_VERSION } from './shared/version';
import {Workflow} from "./shared/workflow";
import { Schema } from "./shared/workflow_schemas";
const app = new App();

export class Middleware extends Stack {
  constructor(
    scope: Construct,
    id: string,
    props: StackProps = {
      // env: devEnv,
      synthesizer: synthesizer(),
    },
  ) {
    super(scope, id, props);

    this.templateOptions.description = '(SO8032) - Stable-Diffusion AWS Extension';

    const apiKeyParam = new CfnParameter(this, 'SdExtensionApiKey', {
      type: 'String',
      description: 'Enter a string of 20 characters that includes a combination of alphanumeric characters',
      allowedPattern: '[A-Za-z0-9]+',
      minLength: 20,
      maxLength: 20,
      // API Key value should be at least 20 characters
      default: '09876543210987654321',
    });

    // Create CfnParameters here
    const s3BucketName = new CfnParameter(this, 'Bucket', {
      type: 'String',
      description: 'New bucket name or Existing Bucket name',
      minLength: 3,
      maxLength: 63,
      // Bucket naming rules: https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html
      allowedPattern: '^(?!.*\\.\\.)(?!xn--)(?!sthree-)(?!.*-s3alias$)(?!.*--ol-s3$)(?!.*\\.$)(?!.*^\\.)[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$',
    });

    const emailParam = new CfnParameter(this, 'Email', {
      type: 'String',
      description: 'Email address to receive notifications',
      allowedPattern: '\\w[-\\w.+]*@([A-Za-z0-9][-A-Za-z0-9]+\\.)+[A-Za-z]{2,14}',
      default: 'example@example.com',
    });

    const logLevel = new CfnParameter(this, 'LogLevel', {
      type: 'String',
      description: 'Log level, example: ERROR | INFO | DEBUG',
      default: 'ERROR',
      allowedValues: ['ERROR', 'INFO', 'DEBUG'],
    });

    const apiEndpointType = new CfnParameter(this, 'ApiEndpointType', {
      type: 'String',
      description: 'API Endpoint, example: REGIONAL | PRIVATE | EDGE',
      default: 'REGIONAL',
      allowedValues: ['REGIONAL', 'PRIVATE', 'EDGE'],
    });

    const isChinaCondition = new CfnCondition(this, 'IsChina', { expression: Fn.conditionEquals(Aws.PARTITION, 'aws-cn') });

    const accountId = Fn.conditionIf(
      isChinaCondition.logicalId,
      '753680513547',
      '366590864501',
    );

    const consoleUrl = Fn.conditionIf(
        isChinaCondition.logicalId,
        'amazonaws.cn',
        'aws.amazon.com',
    );

    // Create resources here

    // The solution currently does not support multi-region deployment, which makes it easy to failure.
    // Therefore, this resource is prioritized to save time.

    const resourceProvider = new ResourceProvider(
      this,
      'ResourcesProvider',
      {
        // when props updated, resource manager will be executed,
        // but if it changes, the resource manager will be executed with 'Update'
        // if the resource manager is executed, it will recheck and create resources for stack
        bucketName: s3BucketName.valueAsString,
        esdVersion: ESD_VERSION,
        timestamp: new Date().toISOString(),
      },
    );

    const s3Bucket = <Bucket>Bucket.fromBucketName(
      this,
      'aigc-bucket',
      resourceProvider.bucketName,
    );

    const ddbTables = new Database(this, 'sd-ddb');

    const commonLayers = new LambdaCommonLayer(this, 'sd-common-layer');

    const restApi = new RestApiGateway(this, apiKeyParam.valueAsString, apiEndpointType, [
      // service
      'api',
      'ping',
      // sd api
      'checkpoints',
      'datasets',
      'users',
      'roles',
      'endpoints',
      'inferences',
      'trainings',
      // comfy api
      'executes',
      'prepare',
      'sync',
      'merge',
      'workflows',
      'schemas',
    ]);

    new MultiUsers(this, {
      synthesizer: props.synthesizer,
      commonLayer: commonLayers.commonLayer,
      multiUserTable: ddbTables.multiUserTable,
      routers: restApi.routers,
    });

    new RootAPI(this, 'RootApi', {
      commonLayer: commonLayers.commonLayer,
      httpMethod: 'GET',
      restApi: restApi.apiGateway,
    });

    new OasApi(this, 'ApiDoc', {
      commonLayer: commonLayers.commonLayer,
      httpMethod: 'GET',
      router: restApi.routers.api,
    });

    new PingApi(this, 'Ping', {
      commonLayer: commonLayers.commonLayer,
      httpMethod: 'GET',
      router: restApi.routers.ping,
    });

    const snsTopics = new SnsTopics(this, 'sd-sns', emailParam);

    new Workflow(this, {
      routers: restApi.routers,
      s3_bucket: s3Bucket,
      workflowsTable: ddbTables.workflowsTable,
      multiUserTable: ddbTables.multiUserTable,
      commonLayer: commonLayers.commonLayer,
      synthesizer: props.synthesizer,
      resourceProvider,
    });

    new Schema(this, {
      routers: restApi.routers,
      s3_bucket: s3Bucket,
      workflowsSchemasTable: ddbTables.workflowsSchemasTable,
      multiUserTable: ddbTables.multiUserTable,
      commonLayer: commonLayers.commonLayer,
      synthesizer: props.synthesizer,
      resourceProvider,
    });

    new Inference(this, {
      routers: restApi.routers,
      s3_bucket: s3Bucket,
      training_table: ddbTables.trainingTable,
      snsTopic: snsTopics.snsTopic,
      sd_inference_job_table: ddbTables.sDInferenceJobTable,
      sd_endpoint_deployment_job_table: ddbTables.sDEndpointDeploymentJobTable,
      checkpointTable: ddbTables.checkpointTable,
      multiUserTable: ddbTables.multiUserTable,
      commonLayer: commonLayers.commonLayer,
      synthesizer: props.synthesizer,
      inferenceErrorTopic: snsTopics.inferenceResultErrorTopic,
      inferenceResultTopic: snsTopics.inferenceResultTopic,
      resourceProvider,
    });

    new CheckpointStack(this, {
      // env: devEnv,
      synthesizer: props.synthesizer,
      checkpointTable: ddbTables.checkpointTable,
      multiUserTable: ddbTables.multiUserTable,
      routers: restApi.routers,
      s3Bucket: s3Bucket,
      commonLayer: commonLayers.commonLayer,
      logLevel: logLevel,
    });

    const ddbComfyTables = new ComfyDatabase(this, 'comfy-ddb');

    const sqsStack = new SqsStack(this, 'comfy-sqs', {
      name: 'SyncComfyMsgJob',
      visibilityTimeout: 900,
    });

    const sqsMergeStack = new SqsStack(this, 'comfy-merge-sqs', {
      name: 'SyncComfyMergeJob',
      visibilityTimeout: 900,
    });

    const apis = new ComfyApiStack(this, 'comfy-api', <ComfyInferenceStackProps>{
      routers: restApi.routers,
      // env: devEnv,
      s3Bucket: s3Bucket,
      executeTable: ddbComfyTables.executeTable,
      syncTable: ddbComfyTables.syncTable,
      msgTable: ddbComfyTables.msgTable,
      multiUserTable: ddbTables.multiUserTable,
      endpointTable: ddbTables.sDEndpointDeploymentJobTable,
      instanceMonitorTable: ddbComfyTables.instanceMonitorTable,
      commonLayer: commonLayers.commonLayer,
      executeSuccessTopic: snsTopics.executeResultSuccessTopic,
      executeFailTopic: snsTopics.executeResultFailTopic,
      snsTopic: snsTopics.snsTopic,
      queue: sqsStack.queue,
      mergeQueue: sqsMergeStack.queue,
    });
    apis.node.addDependency(ddbComfyTables);

    new EndpointStack(this, {
      inferenceErrorTopic: snsTopics.inferenceResultErrorTopic,
      inferenceResultTopic: snsTopics.inferenceResultTopic,
      executeResultSuccessTopic: snsTopics.executeResultSuccessTopic,
      executeResultFailTopic: snsTopics.executeResultFailTopic,
      routers: restApi.routers,
      s3Bucket: s3Bucket,
      multiUserTable: ddbTables.multiUserTable,
      workflowsTable: ddbTables.workflowsTable,
      snsTopic: snsTopics.snsTopic,
      EndpointDeploymentJobTable: ddbTables.sDEndpointDeploymentJobTable,
      syncTable: ddbComfyTables.syncTable,
      instanceMonitorTable: ddbComfyTables.instanceMonitorTable,
      commonLayer: commonLayers.commonLayer,
      queue: sqsStack.queue,
    },
    );

    new TrainDeploy(this, {
      commonLayer: commonLayers.commonLayer,
      synthesizer: props.synthesizer,
      database: ddbTables,
      routers: restApi.routers,
      s3Bucket: s3Bucket,
      snsTopic: snsTopics.snsTopic,
      resourceProvider,
    });

    new DatasetStack(this, {
      commonLayer: commonLayers.commonLayer,
      synthesizer: props.synthesizer,
      database: ddbTables,
      routers: restApi.routers,
      s3Bucket: s3Bucket,
      logLevel,
    });

    new ResourceWaiter(
      this,
      'ResourcesWaiter',
      {
        resourceProvider: resourceProvider,
        restApiGateway: restApi,
        apiKeyParam: apiKeyParam,
        timestamp: new Date().toISOString(),
        apiEndpointType: apiEndpointType.valueAsString,
      },
    );

    // Add ResourcesProvider dependency to all resources
    for (const resource of this.node.children) {
      if (!resourceProvider.instanceof(resource)) {
        resource.node.addDependency(resourceProvider.resources);
      }
    }

    this.addEnvToAllLambdas('ESD_VERSION', ESD_VERSION);
    this.addEnvToAllLambdas('ESD_COMMIT_ID', ESD_COMMIT_ID);
    this.addEnvToAllLambdas('LOG_LEVEL', logLevel.valueAsString);
    this.addEnvToAllLambdas('S3_BUCKET_NAME', s3BucketName.valueAsString);
    this.addEnvToAllLambdas('MULTI_USER_TABLE', ddbTables.multiUserTable.tableName);
    this.addEnvToAllLambdas('ENDPOINT_TABLE_NAME', ddbTables.sDEndpointDeploymentJobTable.tableName);
    this.addEnvToAllLambdas('URL_SUFFIX', Aws.URL_SUFFIX);
    this.addEnvToAllLambdas('ACCOUNT_ID', accountId.toString());
    this.addEnvToAllLambdas('POWERTOOLS_SERVICE_NAME', 'ESD');
    this.addEnvToAllLambdas('POWERTOOLS_TRACE_DISABLED', 'false');
    this.addEnvToAllLambdas('POWERTOOLS_TRACER_CAPTURE_RESPONSE', 'true');
    this.addEnvToAllLambdas('POWERTOOLS_TRACER_CAPTURE_ERROR', 'true');

    // make order for api
    let model: aws_apigateway.Model;
    let gatewayResponse: aws_apigateway.GatewayResponse;
    let gatewayResource: aws_apigateway.Resource;
    this.node.children.forEach(child => {

      if (child instanceof aws_apigateway.Model) {
        if (!model) {
          model = child;
        } else {
          child.node.addDependency(model);
          model = child;
        }
      }

      if (child instanceof aws_apigateway.GatewayResponse) {
        if (!gatewayResponse) {
          gatewayResponse = child;
        } else {
          child.node.addDependency(gatewayResponse);
          gatewayResponse = child;
        }
      }

      if (child instanceof aws_apigateway.Resource) {
        if (!gatewayResource) {
          gatewayResource = child;
        } else {
          child.node.addDependency(gatewayResource);
          gatewayResource = child;
        }
      }

    });

    // Add stackName tag to all resources
    const stackName = Stack.of(this).stackName;
    Tags.of(this).add('stackName', stackName);
    Tags.of(this).add('version', ESD_VERSION);

    new CfnOutput(this, 'EsdVersion', {
      value: ESD_VERSION,
      description: 'ESD Version',
    });

    new CfnOutput(this, 'EsdReleaseTime', {
      value: new Date().toISOString(),
      description: 'ESD Release Time',
    });

    // Adding Outputs for apiGateway and s3Bucket
    new CfnOutput(this, 'ApiGatewayUrl', {
      value: restApi.apiGateway.url,
      description: 'API Gateway URL',
    });

    new CfnOutput(this, 'ApiGatewayUrlToken', {
      value: apiKeyParam.valueAsString,
      description: 'API Gateway Token',
    });

    new CfnOutput(this, 'S3BucketName', {
      value: s3BucketName.valueAsString,
      description: 'S3 Bucket Name',
    });

    new CfnOutput(this, 'EndpointType', {
      value: apiEndpointType.valueAsString,
      description: 'API Endpoint Type',
    });

    new CfnOutput(this, 'SNSTopicName', {
      value: snsTopics.snsTopic.topicName,
      description: 'SNS Topic Name to get train and inference result notification',
    });

    new CfnOutput(this, 'DashboardURL', {
      value: `https://${Aws.REGION}.console.${consoleUrl.toString()}/cloudwatch/home?region=${Aws.REGION}#dashboards/dashboard/ESD`,
      description: 'CloudWatch Dashboard URL',
    });

    new CfnOutput(this, 'ApiDoc', {
      value: `https://aws-gcr-solutions.s3.amazonaws.com/extension-for-stable-diffusion-on-aws/oas_${ESD_VERSION}.json`,
      description: 'API Doc - OAS3',
    });

    new CfnOutput(this, 'TemplateForSDOnEC2', {
      value: `https://aws-gcr-solutions.s3.amazonaws.com/extension-for-stable-diffusion-on-aws/sd_${ESD_VERSION}.yaml`,
      description: 'Create New or Update EC2 Stack for SD (Global Only)',
    });

    new CfnOutput(this, 'TemplateForComfyOnEC2', {
      value: `https://aws-gcr-solutions.s3.amazonaws.com/extension-for-stable-diffusion-on-aws/comfy_${ESD_VERSION}.yaml`,
      description: 'Create New or Update EC2 Stack for Comfy (Global Only)',
    });

    new CfnOutput(this, 'TemplateForCurrentStack', {
      value: `https://aws-gcr-solutions.s3.amazonaws.com/stable-diffusion-aws-extension-github-mainline/${ESD_VERSION}/custom-domain/Extension-for-Stable-Diffusion-on-AWS.template.json`,
      description: 'Current stack template source',
    });

  }

  addEnvToAllLambdas(variableName: string, value: string) {
    this.node.children.forEach(child => {
      if (child instanceof Function) {
        child.addEnvironment(variableName, value);
      }
    });
  }

}

new Middleware(
  app,
  STACK_ID,
  {
    // env: devEnv,
    synthesizer: synthesizer(),
  },
);

app.synth();
// below lines are required if your application has Docker assets
if (process.env.USE_BSS) {
  Aspects.of(app).add(new CompositeECRRepositoryAspect());
}

function synthesizer() {
  return process.env.USE_BSS
    ? new BootstraplessStackSynthesizer()
    : undefined;
}
