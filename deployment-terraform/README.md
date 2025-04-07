# AWS Certified Cloud Practitioner (CLF-C02) Practice Exam WebApp Deployment on AWS

This directory contains Terraform configuration files to deploy the AWS CLF-C02 Practice Exam application to AWS using S3 static website hosting and CloudFront for global content delivery.

## Overview

Terraform configuration files create and configure the following AWS resources:

1. **S3 Bucket** - Configured for static website hosting
2. **S3 Bucket Policy** - Allows public read access to the bucket contents
3. **CloudFront Distribution** - Provides global content delivery with HTTPS support

## Prerequisites

Before using these Terraform files, ensure you have:

1. [Terraform](https://www.terraform.io/downloads.html) installed (version 1.2.0 or newer)
2. AWS CLI installed and configured with appropriate credentials
3. Proper AWS IAM permissions to create and manage S3 buckets and CloudFront distributions

## Usage

### Deployment

1. Initialize the Terraform working directory:
   ```bash
   terraform init
   ```

2. Preview the changes that will be made:
   ```bash
   terraform plan
   ```
   
   You can specify a custom bucket name using the `-var` flag:
   ```bash
   terraform plan -var="bucket_name=my-custom-bucket-name"
   ```

3. Apply the changes to create the infrastructure:
   ```bash
   terraform apply
   ```
   
   Or with a custom bucket name:
   ```bash
   terraform apply -var="bucket_name=my-custom-bucket-name"
   ```

4. After successful deployment, Terraform will output:
   - S3 bucket name
   - S3 website endpoint URL
   - CloudFront distribution ID
   - CloudFront domain name URL (use this to access your application)

### Cleanup

To remove all resources created by Terraform:

```bash
terraform destroy
```

This will:
1. Delete all files from the S3 bucket
2. Delete the CloudFront distribution
3. Delete the S3 bucket

## Configuration Variables

You can customize the deployment by modifying the following variables in `variables.tf` or by passing them as command-line arguments:

| Variable | Description | Default |
|----------|-------------|---------|
| `aws_region` | AWS Region where the S3 bucket will be created | `us-east-1` |
| `bucket_name` | Name of the S3 bucket (if not specified, a random name will be generated) | `null` |
| `webapp_source_dir` | Local directory path containing the web application files | `../WebApp` |
| `exclude_file_extensions` | File extensions to exclude from uploading to S3 | `.ps1`, `.py`, `.pyc`, `.git`, `.gitignore`, `.DS_Store`, `.sh` |
| `exclude_directories` | Directory names to exclude from uploading to S3 | `deployment-python`, `.git`, `__pycache__`, `.github`, `.vscode`, `deployment-terraform` |

## File Structure

- `providers.tf` - AWS provider configuration with required version ≥ 1.2.0
- `variables.tf` - Input variables definition
- `main.tf` - Main resource definitions (S3, CloudFront, file uploads)
- `outputs.tf` - Output values definition

## How It Works

1. **S3 Bucket Creation**: Creates an S3 bucket with a specified or randomly generated name (using `random_id` resource).
2. **Website Configuration**: Configures the bucket for static website hosting with index.html and error.html documents.
3. **Public Access**: Disables block public access settings and applies a bucket policy to allow public read access.
4. **File Upload**: Uses the `aws_s3_object` resource to upload all web application files to the S3 bucket, excluding specified file types and directories.
5. **Content Types**: Automatically sets appropriate MIME types and cache control headers based on file extensions.
6. **CloudFront Distribution**: Creates a CloudFront distribution pointing to the S3 website endpoint for global content delivery with HTTPS support.

## Notes

- The CloudFront distribution can take 15-30 minutes to fully deploy.
- The S3 website endpoint will be available immediately after deployment, but it only supports HTTP.