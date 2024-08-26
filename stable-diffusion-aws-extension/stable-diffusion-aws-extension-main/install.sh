#!/bin/bash

# Warning: This script is used to install the initial support for client and workshop
# Warning: For keeping the same version of the initial support

export INITIAL_SUPPORT_COMMIT_ROOT=bef51aed032c0aaa5cfd80445bc4cf0d85b408b5
export INITIAL_SUPPORT_COMMIT_CONTROLNET=2a210f0489a4484f55088159bbfa51aaf73e10d9
export INITIAL_SUPPORT_COMMIT_TILEDVAE=f9f8073e64f4e682838f255215039ba7884553bf
export INITIAL_SUPPORT_COMMIT_REMBG=a4c07b857e73f3035f759876797fa6de986def3d
export INITIAL_SUPPORT_COMMIT_REACTOR=0185d7a2afa4a3c76b304314233a1cafd1cf4842

rm -rf stable-diffusion-webui

# Clone stable-diffusion-webui
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git --branch master --single-branch
# Go to stable-diffusion-webui directory
cd stable-diffusion-webui
# Reset to specific commit
git reset --hard ${INITIAL_SUPPORT_COMMIT_ROOT}

# Go to "extensions" directory
cd extensions

# Clone stable-diffusion-aws-extension
git clone https://github.com/awslabs/stable-diffusion-aws-extension.git --branch main
# Checkout aigc branch
cd stable-diffusion-aws-extension
cd ..

# Clone sd-webui-controlnet
git clone https://github.com/Mikubill/sd-webui-controlnet.git --branch main --single-branch
# Go to sd-webui-controlnet directory and reset to specific commit
cd sd-webui-controlnet
git reset --hard ${INITIAL_SUPPORT_COMMIT_CONTROLNET}
cd ..

# Clone Tiled VAE
git clone https://github.com/pkuliyi2015/multidiffusion-upscaler-for-automatic1111.git --branch main --single-branch
cd multidiffusion-upscaler-for-automatic1111
git reset --hard ${INITIAL_SUPPORT_COMMIT_TILEDVAE}
cd ..

git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui-rembg.git --branch master --single-branch
cd stable-diffusion-webui-rembg
git reset --hard ${INITIAL_SUPPORT_COMMIT_REMBG}
cd ..

# Clone sd-webui-reactor
git clone https://github.com/Gourieff/sd-webui-reactor.git --branch main --single-branch
# Go to reactor directory and reset to specific commit
cd sd-webui-reactor
git reset --hard ${INITIAL_SUPPORT_COMMIT_REACTOR}
cd ..

