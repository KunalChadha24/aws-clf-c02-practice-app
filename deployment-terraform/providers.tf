terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  required_version = ">= 1.2.0"
}

provider "aws" {
  region = var.aws_region
}

# CloudFront requires the AWS provider in us-east-1 region
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}
