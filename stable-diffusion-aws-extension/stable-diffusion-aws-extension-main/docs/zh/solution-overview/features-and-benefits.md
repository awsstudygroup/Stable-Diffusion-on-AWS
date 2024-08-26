## 主要功能

| **开源主项目**  | **支持版本** | **贴士**|
| ------------- | ------------- | ------------- |
|Stable Diffusion WebUI| V 1.8.0| 默认支持的原生/第三方插件如下表 |
|ComfyUI| 605e64f6d3da44235498bf9103d7aab1c95ef211| 需要支持云上推理的custom nodes，皆可通过本方案提供的模版发布功能，一键打包至云上。因此本方案无内置支持的custom node，用户可灵活选择安装并打包上传。|
|Kohya_ss|V0.8.3|支持基于SD 1.5 & SDXL的LoRa模型训练|

本方案支持以下 Stable Diffusion WebUI 的原生功能/第三方插件的云上工作。其他插件需求可以通过[BYOC（Bring Your Own Container）](../developer-guide/byoc.md)来支持。

| **功能**             | **支持版本** |  **注释** |
| ------------- | ------------- | ------------- |
| [Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui){:target="_blank"}  | V1.8.0  | 新增支持LCM进入官方sampler，SDXL-inpaint models等|
| [txt2img](https://github.com/AUTOMATIC1111/stable-diffusion-webui){:target="_blank"}  | V1.8.0  | |
| [img2img](https://github.com/AUTOMATIC1111/stable-diffusion-webui){:target="_blank"}  | V1.8.0  | 支持除batch外的所有功能|
| [LoRa](https://github.com/AUTOMATIC1111/stable-diffusion-webui){:target="_blank"}  | V1.2.1  | |
| [ControlNet](https://github.com/Mikubill/sd-webui-controlnet){:target="_blank"}  | V1.1.410  | 支持SDXL + ControlNet推理 |
| [Tiled Diffusion & VAE](https://github.com/pkuliyi2015/multidiffusion-upscaler-for-automatic1111.git){:target="_blank"}  | f9f8073e64f4e682838f255215039ba7884553bf  | 图片超分插件 |
| [ReActor for Stable Diffusion](https://github.com/Gourieff/sd-webui-reactor){:target="_blank"} | 0.6.1 | 目前效果最好且持续更新的人物换脸插件 |
| [Extras](https://github.com/AUTOMATIC1111/stable-diffusion-webui){:target="_blank"}  | V1.8.0  | API|
| [rembg](https://github.com/AUTOMATIC1111/stable-diffusion-webui-rembg.git){:target="_blank"}  | 3d9eedbbf0d585207f97d5b21e42f32c0042df70  | API方式支持背景移除功能 |
| [kohya_ss](https://github.com/bmaltais/kohya_ss){:target="_blank"}  |  支持基于SD 1.5 & SDXL的LoRa模型训练 |


## 产品优势

* **安装便捷**。本解决方案使用 CloudFormation 一键部署亚马逊云科技中间件，搭配社区原生 Stable Diffusion WebUI 插件安装形式一键安装，即可赋能用户快速使用 Amazon SageMaker 云上资源，进行推理、训练和调优工作。
* **社区原生**。该方案以插件形式实现，用户无需改变现有Web用户界面的使用习惯。此外，该方案的代码是开源的，采用非侵入式设计，有助于用户快速跟上社区相关功能的迭代，例如备受欢迎的ControlNet和LoRa等插件。
* **可扩展性强**。本解决方案将WebUI界面与后端分离，WebUI可以在支持的终端启动而没有GPU的限制；原有训练，推理等任务通过插件所提供的功能迁移到Amazon SageMaker，为用户提供弹性计算资源、降低成本、提高灵活性和可扩展性。
