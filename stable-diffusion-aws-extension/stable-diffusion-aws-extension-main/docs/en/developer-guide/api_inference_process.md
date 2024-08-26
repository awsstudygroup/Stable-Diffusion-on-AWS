## How-to inference on Stable Diffusion through API

- Create Endpoint through `CreateEndpoint`
- Upload model file through `CreateCheckpoint`, Please refer to: `API Upload Checkpoint Process`
- Select `Async inference` or `Real-time inference`

### Async inference
- Create an inference job through `CreateInferenceJob`
- Based on the presigned address `api_params_s3_upload_url` returned by `CreatInferenceJob` Upload inference parameters
- Start an inference job through `StartInferenceJob`
- Get an inference job through `GetInferenceJob`, check the status, and stop the request if successful

### Real-time inference
- Create an inference job through `CreateInferenceJob`
- Based on the pre signed address `api_params_s3_upload_url` returned by `CreatInferenceJob` Upload inference parameters
- Starting the inference job through `StartInferenceJob`, the real-time inference job will get the inference result in this interface

## How-to inference on ComfyUI through API

### Async inference
- Create Endpoint through `CreateEndpoint`
- Create an inference job through `CreateExecute`
- Get an inference job through `GetExcute`, check the status, and stop the request if successful
