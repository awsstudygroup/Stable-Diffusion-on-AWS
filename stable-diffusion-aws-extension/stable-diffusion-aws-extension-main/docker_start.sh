#!/bin/bash

set -euxo pipefail

if [ -f "/etc/environment" ]; then
    source /etc/environment
fi

export SERVICE_TYPE="comfy"
export CONTAINER_NAME="esd_container"
export AWS_REGION=$(aws configure get region)
export COMMON_FILES_PREFIX="aws-gcr-solutions-$AWS_REGION/stable-diffusion-aws-extension-github-mainline"

CUR_PATH=$(realpath ./)
CONTAINER_PATH=$(realpath ./container)
sudo rm -rf "$CONTAINER_PATH/sync_lock"
sudo rm -rf "$CONTAINER_PATH/s5cmd_lock"
SUPERVISORD_FILE="$CONTAINER_PATH/supervisord.conf"
START_SH=$(realpath ./build_scripts/inference/start.sh)
START_PY=$(realpath ./build_scripts/comfy/serve.py)
COMFY_PROXY=$(realpath ./build_scripts/comfy/comfy_proxy.py)
COMFY_EXT=$(realpath ./build_scripts/comfy/ComfyUI-AWS-Extension)
IMAGE_SH=$(realpath ./docker_image.sh)

# Check if the repository already exists
if aws ecr describe-repositories --region "$AWS_REGION" --repository-names "$CONTAINER_NAME" >/dev/null 2>&1; then
    echo "ECR repository '$CONTAINER_NAME' already exists."
else
    echo "ECR repository '$CONTAINER_NAME' does not exist. Creating..."
    aws ecr create-repository --repository-name --region "$AWS_REGION" "$CONTAINER_NAME" | jq .
    echo "ECR repository '$CONTAINER_NAME' created successfully."
fi

aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "366590864501.dkr.ecr.$AWS_REGION.amazonaws.com"
PUBLIC_BASE_IMAGE="366590864501.dkr.ecr.$AWS_REGION.amazonaws.com/esd-inference:$ESD_VERSION"
docker pull "$PUBLIC_BASE_IMAGE"

export release_image="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$CONTAINER_NAME"

echo "Starting container..."

total_memory=$(cat /proc/meminfo | grep 'MemTotal' | awk '{print $2}')
total_memory_mb=$((total_memory / 1024))
echo "total_memory_mb: $total_memory_mb"
export limit_memory_mb=$((total_memory_mb - 2048))
echo "limit_memory_mb: $limit_memory_mb"

generate_process(){
  init_port=$1
  export PROGRAM_NAME="comfy_$init_port"
  COMFY_WORKFLOW_FILE="$CONTAINER_PATH/$PROGRAM_NAME"

  WORKFLOW_NAME_TMP=""

  if [ -f "$COMFY_WORKFLOW_FILE" ]; then
    WORKFLOW_NAME_TMP=$(cat "$COMFY_WORKFLOW_FILE")
  fi

  if [ -z "$WORKFLOW_NAME_TMP" ]; then
    if [ "$init_port" -eq "10000" ]; then
        WORKFLOW_NAME_TMP="default"
    else
        WORKFLOW_NAME_TMP="local"
    fi
  fi

  echo "$WORKFLOW_NAME_TMP" > "$COMFY_WORKFLOW_FILE"

  export MASTER_PROCESS=false
  if [ "$init_port" -eq "10000" ]; then
      export MASTER_PROCESS=true
  fi

  DOCKER_FILE="ARG BASE_IMAGE
FROM \$BASE_IMAGE

#RUN apt-get update -y && \
#    apt-get install ffmpeg -y && \
#    rm -rf /var/lib/apt/lists/*

WORKDIR /home/ubuntu/ComfyUI"

  if [ ! -f "$CONTAINER_PATH/$PROGRAM_NAME.Dockerfile" ]; then
    echo "$DOCKER_FILE" > "$CONTAINER_PATH/$PROGRAM_NAME.Dockerfile"
  fi

  START_HANDLER="#!/bin/bash
set -euxo pipefail

WORKFLOW_NAME=\$(cat $CONTAINER_PATH/$PROGRAM_NAME)

if [ \"\$WORKFLOW_NAME\" = \"default\" ] || [ \"\$WORKFLOW_NAME\" = \"local\" ]; then
  BASE_IMAGE=$PUBLIC_BASE_IMAGE
else
  BASE_IMAGE=$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$CONTAINER_NAME:\$WORKFLOW_NAME
  aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
  docker pull $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/esd_container:\$WORKFLOW_NAME
fi

sudo mkdir -p $CONTAINER_PATH/output/$PROGRAM_NAME
sudo mkdir -p $CONTAINER_PATH/temp/$PROGRAM_NAME

sudo chmod -R 777 $CONTAINER_PATH/output/$PROGRAM_NAME
sudo chmod -R 777 $CONTAINER_PATH/temp/$PROGRAM_NAME

docker build -f $CONTAINER_PATH/$PROGRAM_NAME.Dockerfile --build-arg BASE_IMAGE=\"\$BASE_IMAGE\" -t $PROGRAM_NAME .
docker stop $PROGRAM_NAME || true
docker rm $PROGRAM_NAME || true
docker run -v $(realpath ~/.aws):/root/.aws \\
           -v $CONTAINER_PATH:/container \\
           -v $CONTAINER_PATH/conda:/home/ubuntu/conda \\
           -v $START_SH:/start.sh:ro \\
           -v $START_PY:/serve.py:ro \\
           -v $COMFY_PROXY:/comfy_proxy.py:ro \\
           -v $COMFY_EXT:/ComfyUI-AWS-Extension:ro \\
           --gpus all \\
           -e IMAGE_HASH=$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/esd_container \\
           -e ACCOUNT_ID=$ACCOUNT_ID \\
           -e BASE_IMAGE=\$BASE_IMAGE \\
           -e SERVICE_TYPE=$SERVICE_TYPE \\
           -e ON_EC2=true \\
           -e DISABLE_AUTO_SYNC=false \\
           -e COMFY_ENDPOINT=name \\
           -e S3_BUCKET_NAME=$COMFY_BUCKET_NAME \\
           -e AWS_REGION=$AWS_REGION \\
           -e AWS_DEFAULT_REGION=$AWS_REGION \\
           -e COMFY_API_URL=$COMFY_API_URL \\
           -e COMFY_API_TOKEN=$COMFY_API_TOKEN \\
           -e ESD_VERSION=$ESD_VERSION \\
           -e COMFY_BUCKET_NAME=$COMFY_BUCKET_NAME \\
           -e MASTER_PROCESS=$MASTER_PROCESS \\
           -e PROGRAM_NAME=$PROGRAM_NAME \\
           -e WORKFLOW_NAME_FILE=/container/$PROGRAM_NAME \\
           --name $PROGRAM_NAME \\
           -p $init_port:8188 \\
           --memory ${limit_memory_mb}mb \\
           $PROGRAM_NAME"

  echo "$START_HANDLER" > "$CONTAINER_PATH/$PROGRAM_NAME.sh"
  chmod +x "$CONTAINER_PATH/$PROGRAM_NAME.sh"

  # shellcheck disable=SC2129
  echo "[program:$PROGRAM_NAME]" >> "$SUPERVISORD_FILE"
  echo "directory=$CUR_PATH" >> "$SUPERVISORD_FILE"
  echo "command=$CONTAINER_PATH/$PROGRAM_NAME.sh" >> "$SUPERVISORD_FILE"
  echo "startretries=2" >> "$SUPERVISORD_FILE"
  echo "stdout_logfile=$CONTAINER_PATH/$PROGRAM_NAME.log" >> "$SUPERVISORD_FILE"
  echo "stderr_logfile=$CONTAINER_PATH/$PROGRAM_NAME.log" >> "$SUPERVISORD_FILE"
  echo "" >> "$SUPERVISORD_FILE"
}

download_so(){
  file_name=$1
  if [ ! -f "/home/ubuntu/conda/lib/$file_name" ]; then
    echo "cp s3://$COMMON_FILES_PREFIX/so/$file_name $CONTAINER_PATH/conda/lib/" >> /tmp/s5cmd.txt
  fi
}

echo "---------------------------------------------------------------------------------"
# init default workflow for all users
if [ ! -d "$CONTAINER_PATH/workflows/default/ComfyUI/venv" ]; then
  tar_file="$CONTAINER_PATH/default.tar"

  if [ ! -f "$tar_file" ]; then
      mkdir -p "$CONTAINER_PATH/workflows"
      start_at=$(date +%s)
      s5cmd cp "s3://$COMMON_FILES_PREFIX/$ESD_VERSION/comfy.tar" "$tar_file"
      end_at=$(date +%s)
      export DOWNLOAD_FILE_SECONDS=$((end_at-start_at))
  fi
  start_at=$(date +%s)
  rm -rf "$CONTAINER_PATH/workflows/default"
  mkdir -p "$CONTAINER_PATH/workflows/default"
  tar --overwrite -xf "$tar_file" -C "$CONTAINER_PATH/workflows/default/"
  rm -rf "$CONTAINER_PATH/workflows/local"
  mkdir -p "$CONTAINER_PATH/workflows/local"
  tar --overwrite -xf "$tar_file" -C "$CONTAINER_PATH/workflows/local/"
  end_at=$(date +%s)
  export DECOMPRESS_SECONDS=$((end_at-start_at))
  cd "$CONTAINER_PATH/workflows/default/ComfyUI"

  rm -rf "$CONTAINER_PATH/workflows/local/ComfyUI/custom_nodes/ComfyUI-Manager"

  echo "cp s3://$COMMON_FILES_PREFIX/models/vae-ft-mse-840000-ema-pruned.safetensors models/vae/" > /tmp/models.txt
  echo "cp s3://$COMMON_FILES_PREFIX/models/majicmixRealistic_v7.safetensors models/checkpoints/" >> /tmp/models.txt
  echo "cp s3://$COMMON_FILES_PREFIX/models/v1-5-pruned-emaonly.ckpt models/checkpoints/" >> /tmp/models.txt
  echo "cp s3://$COMMON_FILES_PREFIX/models/mm_sd_v15_v2.ckpt models/animatediff_models/" >> /tmp/models.txt
  s5cmd run /tmp/models.txt

fi

rm -rf /tmp/s5cmd.txt
download_so "libcufft.so.10"
download_so "libcurand.so.10"
download_so "libcublasLt.so.11"
download_so "libonnxruntime_providers_cuda.so"
download_so "libcublas.so.11"
download_so "libcudart.so.11.0"
if [ -f "/tmp/s5cmd.txt" ]; then
  s5cmd run /tmp/s5cmd.txt
fi

SUPERVISOR_CONF="[supervisord]
nodaemon=true
autostart=true
autorestart=true
directory=$CUR_PATH

[inet_http_server]
port=127.0.0.1:9001

[rpcinterface:supervisor]
supervisor.rpcinterface_factory=supervisor.rpcinterface:make_main_rpcinterface

[supervisorctl]
logfile=/dev/stdout
"

echo "$SUPERVISOR_CONF" > "$SUPERVISORD_FILE"

echo "[program:image]" >> "$SUPERVISORD_FILE"
echo "directory=$CUR_PATH" >> "$SUPERVISORD_FILE"
echo "command=$IMAGE_SH" >> "$SUPERVISORD_FILE"
echo "startretries=1" >> "$SUPERVISORD_FILE"
echo "stdout_logfile=$CONTAINER_PATH/image.log" >> "$SUPERVISORD_FILE"
echo "stderr_logfile=$CONTAINER_PATH/image.log" >> "$SUPERVISORD_FILE"
echo "" >> "$SUPERVISORD_FILE"

if [ -z "$PROCESS_NUMBER" ]; then
  echo "PROCESS_NUMBER not set"
  exit 1
fi

init_port=9999
USER_TOTAL=$((PROCESS_NUMBER + 1))
for i in $(seq 1 "$USER_TOTAL"); do
    init_port=$((init_port + 1))
    generate_process $init_port
done

supervisorctl -c "$SUPERVISORD_FILE" shutdown || true

supervisord -c "$SUPERVISORD_FILE" | grep -v 'uncaptured python exception'

exit 1
