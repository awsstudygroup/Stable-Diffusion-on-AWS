import { JsonSchema, JsonSchemaType, JsonSchemaVersion } from 'aws-cdk-lib/aws-apigateway';

export const SCHEMA_DEBUG: JsonSchema = {
  type: JsonSchemaType.OBJECT,
  title: 'Response Model Debug',
  schema: JsonSchemaVersion.DRAFT7,
  description: 'Debugging information for Lambda Function',
  properties: {
    function_url: {
      type: JsonSchemaType.STRING,
      format: 'uri',
      description: 'URL to Lambda Function',
    },
    log_url: {
      type: JsonSchemaType.STRING,
      format: 'uri',
      description: 'URL to CloudWatch Logs',
    },
    trace_url: {
      type: JsonSchemaType.STRING,
      format: 'uri',
      description: 'URL to X-Ray Trace',
    },
  },
  required: [
    'function_url',
    'log_url',
    'trace_url',
  ],
};


export const SCHEMA_REQUEST_ID: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Request ID by API Gateway',
  format: 'uuid',
};

export const SCHEMA_LAST_KEY: JsonSchema = {
  oneOf: [
    {
      type: JsonSchemaType.NULL,
      description: 'Last Key for Pagination',
    },
    {
      type: JsonSchemaType.STRING,
      description: 'Last Key for Pagination',
    },
  ],
};

export const SCHEMA_MESSAGE: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'API Operate Message',
};

// API Gateway Validator or Lambda Response
export const SCHEMA_202: JsonSchema = {
      type: JsonSchemaType.OBJECT,
      schema: JsonSchemaVersion.DRAFT7,
      title: 'Response Model 202',
      description: 'Schema for an API response with a 202 Accepted status. Since the 202 status indicates that the request has been accepted for processing, this schema does not define any properties for the response body.',
      properties: {
        statusCode: {
          type: JsonSchemaType.INTEGER,
          enum: [
            202,
          ],
        },
        debug: SCHEMA_DEBUG,
        message: {
          type: JsonSchemaType.STRING,
        },
      },
      required: [
        'statusCode',
        'debug',
        'message',
      ],
    }
;

export const SCHEMA_204: JsonSchema = {
  type: JsonSchemaType.OBJECT,
  schema: JsonSchemaVersion.DRAFT7,
  title: 'Response Model 204',
  description: 'Schema for an API response with a 204 No Content status. Since the 204 status indicates that there is no content in the response, this schema does not define any properties for the response body.',
  properties: {},
  additionalProperties: false,
}
;

export const SCHEMA_400: JsonSchema = {
  type: JsonSchemaType.OBJECT,
  description: 'Bad Request',
  schema: JsonSchemaVersion.DRAFT7,
  title: 'Response Model 400',
  properties: {
    statusCode: {
      type: JsonSchemaType.INTEGER,
      enum: [
        400,
      ],
    },
    requestId: SCHEMA_REQUEST_ID,
    debug: SCHEMA_DEBUG,
    message: SCHEMA_MESSAGE,
  },
  required: [
    'statusCode',
    'message',
  ],
}
;


export const SCHEMA_401: JsonSchema = {
  type: JsonSchemaType.OBJECT,
  description: 'Unauthorized',
  schema: JsonSchemaVersion.DRAFT7,
  title: 'Response Model 401',
  properties: {
    statusCode: {
      type: JsonSchemaType.INTEGER,
      enum: [
        401,
      ],
    },
    debug: SCHEMA_DEBUG,
    message: {
      type: JsonSchemaType.STRING,
      enum: ['Unauthorized'],
    },
  },
  required: [
    'statusCode',
    'debug',
    'message',
  ],
}
;


export const SCHEMA_403: JsonSchema = {
  type: JsonSchemaType.OBJECT,
  description: 'Forbidden',
  title: 'Response Model 403',
  schema: JsonSchemaVersion.DRAFT7,
  properties: {
    requestId: SCHEMA_REQUEST_ID,
    message: {
      type: JsonSchemaType.STRING,
      enum: ['Forbidden'],
    },
  },
  required: [
    'requestId',
    'message',
  ],
}
;

export const SCHEMA_404: JsonSchema = {
  type: JsonSchemaType.OBJECT,
  description: 'Not Found',
  title: 'Response Model 404',
  schema: JsonSchemaVersion.DRAFT7,
  properties: {
    statusCode: {
      type: JsonSchemaType.INTEGER,
      enum: [
        404,
      ],
    },
    debug: SCHEMA_DEBUG,
    message: SCHEMA_MESSAGE,
  },
  required: [
    'statusCode',
    'debug',
    'message',
  ],
}
;

export const SCHEMA_504: JsonSchema = {
  type: JsonSchemaType.OBJECT,
  description: 'Gateway Timeout',
  title: 'Response Model 504',
  schema: JsonSchemaVersion.DRAFT7,
  properties: {
    message: SCHEMA_MESSAGE,
    requestId: SCHEMA_REQUEST_ID,
  },
  required: [
    'message',
    'requestId',
  ],
}
;

export const SCHEMA_PERMISSIONS: JsonSchema = {
  type: JsonSchemaType.ARRAY,
  items: {
    type: JsonSchemaType.STRING,
  },
  description: 'Permissions for user',
};

export const SCHEMA_USERNAME: JsonSchema = {
  type: JsonSchemaType.STRING,
  minLength: 1,
  description: 'Username for user',
};

export const SCHEMA_USER_ROLES: JsonSchema = {
  type: JsonSchemaType.ARRAY,
  items: {
    type: JsonSchemaType.STRING,
    minLength: 1,
  },
  minItems: 1,
  maxItems: 20,
  description: 'Roles for user',
};

export const SCHEMA_PASSWORD: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Password for user',
};

export const SCHEMA_CREATOR: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Creator of the dataset',
};

export const SCHEMA_INFER_TYPE: JsonSchema = {
  type: JsonSchemaType.STRING,
  enum: ['Real-time', 'Async'],
  description: 'Inference type',
};

export const SCHEMA_ENDPOINT_NAME: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Name of endpoint',
};

export const SCHEMA_DATASET_NAME: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Name of dataset',
};

export const SCHEMA_DATASET_STATUS: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Status of dataset',
};

export const SCHEMA_DATASET_DESCRIPTION: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Description of dataset',
};

export const SCHEMA_DATASET_TIMESTAMP: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Timestamp of dataset',
};

export const SCHEMA_DATASET_PREFIX: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Prefix of dataset',
};

export const SCHEMA_DATASET_S3: JsonSchema = {
  type: JsonSchemaType.STRING,
  format: 'uri',
  description: 'S3 location of dataset',
};

export const SCHEMA_CHECKPOINT_TYPE: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Type of checkpoint',
  enum: [
    'Stable-diffusion',
    'embeddings',
    'Lora',
    'hypernetworks',
    'ControlNet',
    'VAE',
    'Comfy',
  ],
};

export const SCHEMA_CHECKPOINT_ID: JsonSchema = {
  type: JsonSchemaType.STRING,
  format: 'uuid',
  description: 'ID of checkpoint',
};

export const SCHEMA_CHECKPOINT_STATUS: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Status of checkpoint',
};

export const SCHEMA_TRAIN_ID: JsonSchema = {
  type: JsonSchemaType.STRING,
  pattern: '^[a-f0-9\\-]{36}$',
  description: 'ID of training job',
};

export const SCHEMA_TRAIN_STATUS: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Status of training job',
};


export const SCHEMA_TRAIN_MODEL_NAME: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Model Name',
};

export const SCHEMA_TRAIN_TYPE: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Training Type',
};

export const SCHEMA_TRAINING_TYPE: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Training Type',
};

export const SCHEMA_TRAINING_PARAMS: JsonSchema = {
  type: JsonSchemaType.OBJECT,
  description: 'Training Parameters',
};

export const SCHEMA_TRAIN_CONFIG_PARAMS: JsonSchema = {
  type: JsonSchemaType.OBJECT,
  description: 'Training Configuration Parameters',
  properties: {
    output_name: {
      type: JsonSchemaType.STRING,
      description: 'Output Model Name',
      minLength: 1,
    },
  },
  required: [
    'output_name',
  ],
  additionalProperties: true,
};

export const SCHEMA_TRAIN_PARAMS: JsonSchema = {
  type: JsonSchemaType.OBJECT,
  description: 'Training Parameters',
  additionalProperties: true,
  properties: {
    config_params: SCHEMA_TRAIN_CONFIG_PARAMS,
    training_params: SCHEMA_TRAINING_PARAMS,
    training_type: SCHEMA_TRAINING_TYPE,
  },
  required: [
    'training_params',
    'training_type',
    'config_params',
  ],
};

export const SCHEMA_TRAIN_CREATED: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Created Time of Training Job',
};

export const SCHEMA_TRAIN_SAGEMAKER_NAME: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Name of SageMaker Training Job',
};

export const SCHEMA_ENDPOINT_ID: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'ID of Endpoint',
  pattern: '^[a-f0-9\\-]{36}$',
};

export const SCHEMA_ENDPOINT_TYPE: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Endpoint Type',
  enum: ['Real-time', 'Async'],
};

export const SCHEMA_ENDPOINT_SERVICE_TYPE: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Service Type',
  enum: ['sd', 'comfy'],
};

export const SCHEMA_ENDPOINT_STATUS: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Status of Endpoint',
};

export const SCHEMA_ENDPOINT_INSTANCE_TYPE: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Instance Type',
};

export const SCHEMA_ENDPOINT_AUTOSCALING: JsonSchema = {
  type: JsonSchemaType.BOOLEAN,
  description: 'Autoscaling',
};

export const SCHEMA_ENDPOINT_MAX_INSTANCE_NUMBER: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Maximum number of instances',
  pattern: '^[0-9]+$',
};

export const SCHEMA_ENDPOINT_START_TIME: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Start Time of Endpoint',
  format: 'date-time',
};

export const SCHEMA_ENDPOINT_CURRENT_INSTANCE_COUNT: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Current number of instances',
  pattern: '^[0-9]+$',
};

export const SCHEMA_ENDPOINT_OWNER_GROUP_OR_ROLE: JsonSchema = {
  type: JsonSchemaType.ARRAY,
  description: 'Owner Group or Role',
  items: {
    type: JsonSchemaType.STRING,
  },
};

export const SCHEMA_ENDPOINT_MIN_INSTANCE_NUMBER: JsonSchema = {
  type: JsonSchemaType.STRING,
  pattern: '^[0-9]+$',
  description: 'Minimum number of instances',
};

export const SCHEMA_ENDPOINT_CUSTOM_EXTENSIONS: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Custom Extensions',
};

export const SCHEMA_EXECUTE_PROMPT_ID: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Prompt ID',
  format: 'uuid',
};

export const SCHEMA_EXECUTE_STATUS: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Status of Execute',
};


export const SCHEMA_EXECUTE_NEED_SYNC: JsonSchema = {
  type: JsonSchemaType.BOOLEAN,
  description: 'Need Sync',
};

export const SCHEMA_EXECUTE_PROMPT_PATH: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Prompt Path',
};

export const SCHEMA_WORKFLOW: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Workflow remark',
  pattern: '^[A-Za-z][A-Za-z0-9_]*$',
};

export const SCHEMA_INFERENCE: Record<string, JsonSchema> = {
  img_presigned_urls: {
    type: JsonSchemaType.ARRAY,
    items: {
      type: JsonSchemaType.STRING,
      format: 'uri',
    },
  },
  output_presigned_urls: {
    type: JsonSchemaType.ARRAY,
    items: {
      type: JsonSchemaType.STRING,
      format: 'uri',
    },
  },
  startTime: {
    type: JsonSchemaType.STRING,
    format: 'date-time',
  },
  taskType: {
    type: JsonSchemaType.STRING,
  },
  image_names: {
    type: JsonSchemaType.ARRAY,
    items: {
      type: JsonSchemaType.STRING,
      pattern: '^.+\\.*$',
    },
  },
  params: {
    type: JsonSchemaType.OBJECT,
    additionalProperties: true,
    properties: {
      input_body_presign_url: {
        type: JsonSchemaType.STRING,
        format: 'uri',
      },
      input_body_s3: {
        type: JsonSchemaType.STRING,
        format: 'uri',
      },
      output_path: {
        type: JsonSchemaType.STRING,
      },
      sagemaker_inference_instance_type: SCHEMA_ENDPOINT_INSTANCE_TYPE,
      sagemaker_inference_endpoint_id: SCHEMA_ENDPOINT_ID,
      sagemaker_inference_endpoint_name: SCHEMA_ENDPOINT_NAME,
    },
    required: [
      'input_body_s3',
      'sagemaker_inference_instance_type',
      'sagemaker_inference_endpoint_id',
      'sagemaker_inference_endpoint_name',
    ],
  },
  InferenceJobId: {
    type: JsonSchemaType.STRING,
    format: 'uuid',
  },
  status: {
    type: JsonSchemaType.STRING,
  },
  createTime: {
    type: JsonSchemaType.STRING,
    format: 'date-time',
  },
  owner_group_or_role: {
    type: JsonSchemaType.ARRAY,
    items: {
      type: JsonSchemaType.STRING,
    },
  },
  sagemakerRaw: {
    type: JsonSchemaType.OBJECT,
  },
  payload_string: {
    type: JsonSchemaType.STRING,
  },
};

export const SCHEMA_INFERENCE_ASYNC_MODEL: Record<string, JsonSchema> = {
  statusCode: {
    type: JsonSchemaType.NUMBER,
  },
  debug: SCHEMA_DEBUG,
  message: SCHEMA_MESSAGE,
  data: {
    type: JsonSchemaType.OBJECT,
    additionalProperties: true,
    properties: {
      InferenceJobId: SCHEMA_INFERENCE.InferenceJobId,
      status: SCHEMA_INFERENCE.status,
    },
    required: [
      'InferenceJobId',
      'status',
    ],
  },
};

export const SCHEMA_INFERENCE_REAL_TIME_MODEL: Record<string, JsonSchema> = {
  statusCode: {
    type: JsonSchemaType.NUMBER,
  },
  debug: SCHEMA_DEBUG,
  message: SCHEMA_MESSAGE,
  data: {
    type: JsonSchemaType.OBJECT,
    additionalProperties: true,
    properties: SCHEMA_INFERENCE,
  },
};


export const SCHEMA_WORKFLOW_NAME: JsonSchema = {
  type: JsonSchemaType.STRING,
  minLength: 1,
  maxLength: 20,
  pattern: '^[A-Za-z][A-Za-z0-9]*$',
  description: 'Name of workflow',
};

export const SCHEMA_WORKFLOW_IMAGE_URI: JsonSchema = {
  type: JsonSchemaType.STRING,
  minLength: 1,
};

export const SCHEMA_WORKFLOW_PAYLOAD_JSON: JsonSchema = {
  type: JsonSchemaType.STRING,
};

export const SCHEMA_WORKFLOW_STATUS: JsonSchema = {
  type: JsonSchemaType.STRING,
};

export const SCHEMA_WORKFLOW_SIZE: JsonSchema = {
  type: JsonSchemaType.STRING,
};

export const SCHEMA_WORKFLOW_JSON_NAME: JsonSchema = {
  type: JsonSchemaType.STRING,
  minLength: 1,
  maxLength: 20,
  pattern: '^[A-Za-z][A-Za-z0-9_]*$',
  description: 'Name of Workflow Schema',
};

export const SCHEMA_WORKFLOW_JSON_PAYLOAD_JSON: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Payload JSON String of Schema',
  minLength: 1,
};

export const SCHEMA_WORKFLOW_JSON_WORKFLOW: JsonSchema = {
  type: JsonSchemaType.STRING,
};

export const SCHEMA_WORKFLOW_JSON_CREATED: JsonSchema = {
  type: JsonSchemaType.STRING,
};
