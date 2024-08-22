# Stable Diffusion on AWS - Deployment Guide

### **Overview**
This guide provides detailed instructions to deploy a Stable Diffusion Proof of Concept (POC) product on AWS. The deployment involves setting up the Stable Diffusion WebUI, deploying middleware, and configuring APIs. The deployed solution can be accessed either through a user interface (UI) or directly via API calls.

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

