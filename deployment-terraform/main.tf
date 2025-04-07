locals {
  # Generate a random bucket name if not provided
  bucket_name = var.bucket_name != null ? var.bucket_name : "aws-clf-c02-practice-exam-app-${random_id.suffix.hex}"
  
  # Mime types for specific file extensions to ensure proper content types
  mime_types = {
    "html" = "text/html"
    "css"  = "text/css"
    "js"   = "application/javascript"
    "json" = "application/json"
    "png"  = "image/png"
    "jpg"  = "image/jpeg"
    "jpeg" = "image/jpeg"
    "gif"  = "image/gif"
    "svg"  = "image/svg+xml"
    "ico"  = "image/x-icon"
    "md"   = "text/markdown"
  }
  
  # Cache control settings for different file types
  cache_control = {
    "html" = "max-age=3600"
    "css"  = "max-age=86400"
    "js"   = "max-age=86400"
    "json" = "max-age=3600"
    "md"   = "max-age=3600"
    "default" = "max-age=604800"
  }
  
  # S3 website endpoint
  s3_website_endpoint = "${aws_s3_bucket_website_configuration.website.website_endpoint}"
}

# Generate a random suffix for the S3 bucket name if not provided
resource "random_id" "suffix" {
  byte_length = 4
}

# Create the S3 bucket
resource "aws_s3_bucket" "website" {
  bucket = local.bucket_name
  
  tags = {
    Name        = "AWS CLF-C02 Practice Exam App"
    Environment = "Production"
    Terraform   = "true"
  }
}

# Configure the bucket for static website hosting
resource "aws_s3_bucket_website_configuration" "website" {
  bucket = aws_s3_bucket.website.id
  
  index_document {
    suffix = "index.html"
  }
  
  error_document {
    key = "error.html"
  }
}

# Disable block public access settings for the bucket
resource "aws_s3_bucket_public_access_block" "website" {
  bucket = aws_s3_bucket.website.id
  
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# Set bucket policy to allow public read access
resource "aws_s3_bucket_policy" "website" {
  bucket = aws_s3_bucket.website.id
  
  # Wait for the public access block to be disabled
  depends_on = [aws_s3_bucket_public_access_block.website]
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.website.arn}/*"
      }
    ]
  })
}

# Get a set of all files in the source directory, respecting ignores
locals {
  # Create a set of files from the source directory
  all_files = fileset(var.webapp_source_dir, "**/*")

  # Filter the files based on exclusions
  filtered_files = {
    for f in local.all_files : f => f
    # Exclude files based on extension
    if !anytrue([for ext in var.exclude_file_extensions : endswith(f, ext)]) &&
    # Exclude files based on directory names within the path
    !anytrue([for dir in var.exclude_directories : contains(split("/", f), dir)])
  }
}


# Upload website files to S3 bucket using the 'source' argument
resource "aws_s3_object" "website_files" {
  # Use the filtered map of files
  for_each = local.filtered_files

  bucket = aws_s3_bucket.website.id
  key    = each.key # The relative path within the bucket

  # Use the source argument to point to the local file
  source = "${var.webapp_source_dir}/${each.value}"

  # Use filemd5 for etag calculation based on the actual file content
  etag = filemd5("${var.webapp_source_dir}/${each.value}")

  # Keep your existing content_type and cache_control logic
  content_type = lookup(
    local.mime_types,
    element(split(".", each.key), length(split(".", each.key)) - 1),
    "binary/octet-stream" # Default MIME type
  )
  cache_control = lookup(
    local.cache_control,
    element(split(".", each.key), length(split(".", each.key)) - 1),
    local.cache_control["default"]
  )

  # Optional: Add depends_on if needed, though usually implicit with bucket creation
  # depends_on = [aws_s3_bucket.website]
}

# Create CloudFront distribution
resource "aws_cloudfront_distribution" "website" {
  provider = aws.us_east_1
  
  origin {
    domain_name = local.s3_website_endpoint
    origin_id   = "S3-Website-${aws_s3_bucket.website.id}"
    
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }
  
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  
  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-Website-${aws_s3_bucket.website.id}"
    
    forwarded_values {
      query_string = false
      
      cookies {
        forward = "none"
      }
    }
    
    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }
  
  price_class = "PriceClass_All"
  
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
  
  viewer_certificate {
    cloudfront_default_certificate = true
  }
  
  tags = {
    Name        = "AWS CLF-C02 Practice Exam App"
    Environment = "Production"
    Terraform   = "true"
  }
}
