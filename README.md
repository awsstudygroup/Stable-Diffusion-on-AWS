# Stable Diffusion on AWS - Deployment Guide SD UI

### **Overview**
This guide provides detailed instructions to deploy a Stable Diffusion Proof of Concept (POC) product on AWS. The deployment involves setting up the Stable Diffusion WebUI, deploying middleware, and configuring APIs. The deployed solution can be accessed either through a user interface (UI) or directly via API calls.

![Architecture](/arc/architecture.jpg)

### **Estimated Deployment Time**
Approximately 20 minutes

### **Prerequisites**
- **Linux-Based Computer**: A Linux machine is required for initial setup and deployment commands.
- **AWS Account**: Ensure you have an active AWS account with permissions to create resources like EC2 instances, S3 buckets, IAM roles, and CloudFormation stacks.
- **AWS CLI**: Install and configure the AWS Command Line Interface (CLI) on your Linux machine to interact with AWS services.

### **Deployment Summary**
This deployment is divided into the following steps:
- **Step 0**: Deploy the Stable Diffusion WebUI (if using the UI interface).
- **Step 1**: Deploy the middleware using AWS CloudFormation.
- **Step 2**: Configure the API URL and API Token to link the frontend with backend resources.

---

## **Step 0: Deploy Stable Diffusion WebUI**

### **Linux Deployment**:
1. **Log into AWS Management Console**:
   - Open your browser and go to the [AWS Management Console](https://console.aws.amazon.com/).
   - Ensure you are logged into the correct AWS account and region where you intend to deploy the solution.

2. **Create the WebUI Stack**:
   - Access the CloudFormation stack deployment page by clicking [this link](https://console.aws.amazon.com/cloudformation/home?#/stacks/create/template?stackName=stable-diffusion-aws&templateURL=https://aws-gcr-solutions.s3.amazonaws.com/extension-for-stable-diffusion-on-aws/sd.yaml).
   - On the **Create Stack** page, click **Next**.

3. **Configure Stack Parameters**:
   - **Stack Name**: Enter a unique name for your stack (e.g., `StableDiffusionWebUI`).
   - **Parameters**: Adjust parameters such as instance types, network configurations, or storage options as needed.

4. **IAM Permissions**:
   - On the **Review** page, acknowledge that AWS CloudFormation might create IAM resources by checking the appropriate box.

5. **Launch the Stack**:
   - Click **Submit** to initiate stack creation. Monitor the creation process in the CloudFormation console.

6. **Access the WebUI**:
   - Once the stack reaches the **CREATE_COMPLETE** status, navigate to the **Outputs** tab in the CloudFormation console.
   - Locate the **WebUIURL** link and click it to access the Stable Diffusion WebUI. Note that setup may take an additional 30 minutes to fully configure internal services.

### **Windows Deployment**:
1. **Launch a Windows Server**:
   - Start a Windows Server instance through the AWS Management Console.

2. **Install NVIDIA Drivers**:
   - Follow the [NVIDIA Driver Installation Guide](https://docs.aws.amazon.com/zh_cn/AWSEC2/latest/WindowsGuide/install-nvidia-driver.html) to install the required GPU drivers.

3. **Install Python**:
   - Download Python 3.10.6 from [Python.org](https://www.python.org/downloads/release/python-3106/) and ensure you add Python to your system path during installation.

4. **Install Git**:
   - Download and install Git from the [Git website](https://git-scm.com/download/win).

5. **Clone the Repository**:
   - Open PowerShell, navigate to the directory where you want to install the WebUI, and run:
     ```bash
     git clone https://github.com/awslabs/stable-diffusion-aws-extension
     ```
   - Navigate to the cloned directory and run the `install.bat` script.

6. **Start WebUI**:
   - In the `stable-diffusion-webui` directory, execute the `webui-user.bat` script to launch the WebUI.

---

## **Step 1: Deploy the Middleware**

1. **Access the AWS Management Console**:
   - Open the [AWS Management Console](https://console.aws.amazon.com/) and verify you’re in the correct region.

2. **Launch the Middleware Stack**:
   - Click on the [Extension-for-Stable-Diffusion-on-AWS.template link](https://console.aws.amazon.com/cloudformation/home?#/stacks/create/template?stackName=stable-diffusion-aws&templateURL=https://aws-gcr-solutions.s3.amazonaws.com/stable-diffusion-aws-extension-github-mainline/latest/custom-domain/Extension-for-Stable-Diffusion-on-AWS.template.json).

3. **Create the CloudFormation Stack**:
   - On the **Create Stack** page, confirm that the correct template URL is pre-filled. Click **Next**.
   - Provide a unique name for your stack on the **Specify Stack Details** page.

4. **Configure Parameters**:
   - **S3 Bucket Name**: Enter a unique name for your S3 bucket (this will store generated images and model data).
   - **Email Address**: Provide a valid email address for notifications.
   - **API Key**: Optionally, enter a 20-character alphanumeric string for the `SdExtensionApiKey` parameter. This key will be used for API authentication.
   - **Log Level**: Set the logging level for Lambda functions (`ERROR`, `INFO`, `DEBUG`).

5. **Review and Deploy**:
   - Review your settings, acknowledge the creation of IAM resources, and click **Submit**.

6. **Monitor Stack Creation**:
   - Monitor the stack creation process in the AWS CloudFormation console. Wait until the stack reaches **CREATE_COMPLETE** status, typically within 15 minutes.

7. **Subscription Confirmation**:
   - Check your email inbox for a subscription confirmation from AWS and confirm the subscription to activate notifications.

---

## **Step 2: Configure API URL and API Token**

1. **Retrieve API Information**:
   - Log in to the [AWS CloudFormation Console](https://console.aws.amazon.com/).
   - Select the relevant stack and navigate to the **Outputs** tab to find the **APIGatewayUrl** and **ApiGatewayUrlToken** values. Copy these for the next steps.

2. **Configure WebUI API Settings**:
   - Open the Stable Diffusion WebUI and go to the **Amazon SageMaker** tab.
   - Paste the **APIGatewayUrl** into the **API URL** field.
   - Paste the **ApiGatewayUrlToken** into the **API Token** field.
   - Use the super admin credentials created during stack setup for **Username** and **Password**.

3. **Test Connection**:
   - Click **Test Connection & Update Setting**. A successful connection will be confirmed, indicating that the frontend is now linked to the backend resources.

4. **Save Configuration**:
   - The WebUI will automatically use this configuration in future sessions.

---

## **Multi-User Management**

After deployment, you can manage multiple users and roles via the Stable Diffusion WebUI.

### **Role Management**

1. **Create and Configure Roles**:
   - Navigate to the **Amazon SageMaker** tab and the **API and User Settings** sub-tab.
   - In the **Role Management** section, view, create, and configure roles as needed.
   - Assign permissions according to your organizational requirements.

2. **Update Role Table**:
   - After creating or modifying roles, refresh the page or click **Next Page** to update the displayed roles.

### **User Management**

1. **Create New Users**:
   - In the **User Management** section, create new users with specific roles and passwords.
   - Refresh the page or click **Next Page** to view newly created users.

2. **Manage Existing Users**:
   - Select a user from the **User Table** to update their role or password.
   - Users can also be deleted from this interface.

### **Permissions Overview**

Below is a summary of the permissions available for different roles:

| **Permission**            | **Scope**    | **Details**                                      |
|---------------------------|--------------|--------------------------------------------------|
| `role:all`                | Roles        | Create, retrieve, update, and delete roles       |
| `user:all`                | Users        | Manage user accounts, including creating, updating, and deleting users |
| `sagemaker_endpoint:all`  | Endpoints    | Create, manage, and delete SageMaker endpoints   |
| `inference:all`           | Inference    | Manage inference jobs                            |
| `checkpoint:all`          | Model Files  | Manage model files, including creating and deleting |
| `train:all`               | Training     | Manage training jobs                             |


# Stable Diffusion on AWS - Deployment Guide Comfy UI
Before you begin deploying the solution, it is recommended to review the information in this guide, including architecture diagrams and region support. Then, follow the instructions below to configure and deploy the solution to your account.

**Estimated Deployment Time:** Approximately 20 minutes

---

## Deployment Overview

Deploying this solution on AWS, specifically the ComfyUI part, involves the following processes:

1. **Step 1:** Deploy the solution's middleware.
2. **Step 2:** Deploy the ComfyUI frontend.

After deployment, refer to the [ComfyUI User Guide](../user-guide/ComfyUI/inference.md) for detailed usage instructions.

---

## Deployment Steps

### Step 1: Deploy the Solution Middleware
This step uses an automated Amazon CloudFormation template to deploy the solution's middleware on AWS.

1. **Login to AWS Console:**  
   Go to the [AWS Management Console](https://console.aws.amazon.com/) and click the link [Extension for Stable Diffusion on AWS](https://console.aws.amazon.com/cloudformation/home?#/stacks/create/template?stackName=stable-diffusion-aws&templateURL=https://aws-gcr-solutions.s3.amazonaws.com/stable-diffusion-aws-extension-github-mainline/latest/custom-domain/Extension-for-Stable-Diffusion-on-AWS.template.json).

2. **Select Region:**  
   By default, the template will launch in the region you're currently logged into. If you need to deploy in a specific AWS region, choose it from the region dropdown in the console navigation bar.

3. **Confirm Template URL:**  
   On the **Create Stack** page, verify that the Amazon S3 URL textbox displays the correct template URL, then click **Next**.

4. **Specify Stack Details:**  
   On the **Specify Stack Details** page, assign a unique name for your solution stack within the account, following naming conventions. Refer to the table below for deployment parameters. Click **Next**.

   | Parameter         | Description                                                  | Recommendation           |
   |:------------------|:-------------------------------------------------------------|:-------------------------|
   | APIEndpointType    | Defines the type of API if API calls are needed. Options are REGIONAL, PRIVATE, or EDGE. | Default: REGIONAL        |
   | Bucket            | Enter a valid new S3 bucket name (or use an existing bucket used for the ComfyUI part of this solution). |                         |
   | email             | Enter a correct email address to receive future notifications. |                         |
   | SdExtensionApiKey | Enter a 20-character alphanumeric string. | Default: "09876543210987654321" |
   | LogLevel          | Choose your preferred Lambda Log level. | Default: ERROR          |

5. **Configure Stack Options:**  
   On the **Configure Stack Options** page, select **Next**.

6. **Review and Deploy:**  
   On the **Review** page, confirm the settings. Ensure you check the box to acknowledge that the template will create Amazon Identity and Access Management (IAM) resources, along with any other required features. Click **Submit** to deploy the stack.

7. **Monitor Stack Status:**  
   In the AWS CloudFormation console, monitor the status column for the stack. You should see the status **CREATE_COMPLETE** within approximately 15 minutes.

   !!! tip "Tip"
   Please check your email inbox for a message with the subject “AWS Notification - Subscription Confirmation.” Click the “Confirm subscription” link in the email and follow the instructions to complete the subscription.

---

### Step 2: Deploy the ComfyUI Frontend

This step installs the ComfyUI frontend, which includes a built-in Chinese localization plugin, workflow publishing to the cloud, and other user-friendly interface enhancements. This is also done via an automated Amazon CloudFormation template.

1. **Login to AWS Console:**  
   Go to the [AWS Management Console](https://console.aws.amazon.com/), click **Create Stack** in the top right corner, and select **With new resources (standard)** to start creating a stack.

2. **Choose Template:**  
   On the **Create Stack** page, select **Choose an existing template**. In the **Specify template** section, choose **Amazon S3 URL** and enter this [deployment template link](https://aws-gcr-solutions.s3.amazonaws.com/extension-for-stable-diffusion-on-aws/comfy.yaml), then click **Next**.

3. **Specify Stack Details:**  
   On the **Specify Stack Details** page, assign a unique name for your solution stack within the account, following naming conventions. Deployment parameters are explained below. Click **Next**.

   !!! tip "Tip"
   The EC2 Key Pair is mainly used for remote connection to the EC2 instance. If you do not have an existing one, refer to the [official guide](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/create-key-pairs.html) to create one.

   | Parameter          | Description                                             | Recommendation                  |
   |:-------------------|:--------------------------------------------------------|:---------------------------------|
   | InstanceType       | The EC2 instance type to be deployed.                   | For inference involving animations or videos, use G6 or G5 instances. |
   | NumberOfInferencePorts | Number of inference environments.                    | Recommended: No more than 5     |
   | StackName          | The stack name from the successful deployment in Step 1.|                                 |
   | keyPairName        | Choose an existing EC2 Key Pair.                        |                                 |

4. **Configure Stack Options:**  
   On the **Configure Stack Options** page, select **Next**.

5. **Review and Deploy:**  
   On the **Review** page, confirm the settings. Ensure you check the box to acknowledge that the template will create Amazon Identity and Access Management (IAM) resources, along with any other required features. Click **Submit** to deploy the stack.

6. **Monitor Stack Status:**  
   In the AWS CloudFormation console, monitor the status column for the stack. You should see the status **CREATE_COMPLETE** within approximately 3 minutes.

7. **Access ComfyUI Frontend:**  
   Select the successfully deployed stack, open **Outputs**, and click the link corresponding to **Designer** to open the deployed ComfyUI frontend. You might need to disable VPN or access the Designer without the 10000 port for proper access. **NumberOfInferencePortsStart** represents the starting port of the inference environment address path. The port address increases sequentially based on the deployment quantity. For example, if **NumberOfInferencePorts** is set to 2, the accessible inference environment addresses will be:
   - http://EC2-address:10001
   - http://EC2-address:10002

   | Role              | Function                                                    | Port                                      |
   |:------------------|:------------------------------------------------------------|:------------------------------------------|
   | Lead Artist / Workflow Manager | Can install new custom nodes, debug workflows on EC2, publish workflows and environments to Amazon SageMaker. It can also call SageMaker resources and select published workflows for inference verification. | http://EC2-address                         |
   | General Artist    | Can enter the interface from this port, select the published workflows by the lead artist, modify inference parameters, and check “Prompt on AWS” to call Amazon SageMaker for inference. | When **NumberOfInferencePorts** is set to 3, the accessible inference environment addresses will be:<ul><li>http://EC2-address:10001</li><li>http://EC2-address:10002</li><li>http://EC2-address:10003</li></ul>|

   !!! tip "Tip"
   After deployment, wait a moment. If you see a message stating “Comfy is Initializing or Starting” when opening the link, it means the backend is initializing the ComfyUI. Please wait a little longer and refresh the page to confirm.

