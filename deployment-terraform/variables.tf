variable "aws_region" {
  description = "AWS Region where the S3 bucket will be created"
  type        = string
  default     = "us-east-1"
}

variable "bucket_name" {
  description = "Name of the S3 bucket for static website hosting"
  type        = string
  default     = null
}

variable "webapp_source_dir" {
  description = "Local directory path containing the web application files"
  type        = string
  default     = "../WebApp"
}

variable "exclude_file_extensions" {
  description = "File extensions to exclude from uploading to S3"
  type        = list(string)
  default     = [".ps1", ".py", ".pyc", ".git", ".gitignore", ".DS_Store", ".sh"]
}

variable "exclude_directories" {
  description = "Directory names to exclude from uploading to S3"
  type        = list(string)
  default     = ["deployment-python", ".git", "__pycache__", ".github", ".vscode", "deployment-terraform"]
}
