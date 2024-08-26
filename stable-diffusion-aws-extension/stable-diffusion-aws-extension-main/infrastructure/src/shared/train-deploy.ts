import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';
import { aws_s3, aws_sns, StackProps } from 'aws-cdk-lib';
import { Resource } from 'aws-cdk-lib/aws-apigateway/lib/resource';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import { Construct } from 'constructs';
import { Database } from './database';
import { ResourceProvider } from './resource-provider';
import { CreateTrainingJobApi } from '../api/trainings/create-training-job';
import { DeleteTrainingJobsApi } from '../api/trainings/delete-training-jobs';
import { GetTrainingJobApi } from '../api/trainings/get-training-job';
import { ListTrainingJobsApi } from '../api/trainings/list-training-jobs';
import { SagemakerTrainingEvents } from '../events/trainings-event';

export interface TrainDeployProps extends StackProps {
  database: Database;
  routers: { [key: string]: Resource };
  s3Bucket: aws_s3.Bucket;
  snsTopic: aws_sns.Topic;
  commonLayer: PythonLayerVersion;
  resourceProvider: ResourceProvider;
}

export class TrainDeploy {
  public readonly deleteTrainingJobsApi: DeleteTrainingJobsApi;
  private readonly resourceProvider: ResourceProvider;

  constructor(scope: Construct, props: TrainDeployProps) {

    this.resourceProvider = props.resourceProvider;

    // Upload api template file to the S3 bucket
    new s3deploy.BucketDeployment(scope, 'DeployApiTemplate', {
      sources: [s3deploy.Source.asset('../middleware_api/common/template')],
      destinationBucket: props.s3Bucket,
      destinationKeyPrefix: 'template',
    });

    const commonLayer = props.commonLayer;
    const routers = props.routers;

    const checkPointTable = props.database.checkpointTable;
    const multiUserTable = props.database.multiUserTable;

    // GET /trainings
    new ListTrainingJobsApi(scope, 'ListTrainingJobs', {
      commonLayer: commonLayer,
      httpMethod: 'GET',
      router: routers.trainings,
      trainTable: props.database.trainingTable,
      multiUserTable: multiUserTable,
    });

    // POST /trainings
    new CreateTrainingJobApi(scope, 'CreateTrainingJob', {
      checkpointTable: checkPointTable,
      commonLayer: commonLayer,
      httpMethod: 'POST',
      router: routers.trainings,
      s3Bucket: props.s3Bucket,
      trainTable: props.database.trainingTable,
      multiUserTable: multiUserTable,
      userTopic: props.snsTopic,
      resourceProvider: this.resourceProvider,
      datasetInfoTable: props.database.datasetInfoTable,
    });

    // DELETE /trainings
    this.deleteTrainingJobsApi = new DeleteTrainingJobsApi(scope, 'DeleteTrainingJobs', {
      router: props.routers.trainings,
      commonLayer: props.commonLayer,
      trainingTable: props.database.trainingTable,
      multiUserTable: multiUserTable,
      httpMethod: 'DELETE',
      s3Bucket: props.s3Bucket,
    },
    );

    // DELETE /trainings/{id}
    new GetTrainingJobApi(scope, 'GetTrainingJob', {
      router: props.routers.trainings,
      commonLayer: props.commonLayer,
      trainingTable: props.database.trainingTable,
      multiUserTable: multiUserTable,
      httpMethod: 'GET',
      s3Bucket: props.s3Bucket,
    },
    );

    new SagemakerTrainingEvents(scope, 'SagemakerTrainingEvents', {
      commonLayer: props.commonLayer,
      trainingTable: props.database.trainingTable,
      checkpointTable: props.database.checkpointTable,
      userTopic: props.snsTopic,
      s3Bucket: props.s3Bucket,
    },
    );

  }
}
