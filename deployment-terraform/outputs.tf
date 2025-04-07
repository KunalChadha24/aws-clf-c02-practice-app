output "s3_bucket_name" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.website.id
}

output "s3_website_endpoint" {
  description = "S3 static website hosting endpoint"
  value       = "http://${aws_s3_bucket_website_configuration.website.website_endpoint}"
}

output "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution"
  value       = aws_cloudfront_distribution.website.id
}

output "cloudfront_domain_name" {
  description = "Domain name of the CloudFront distribution"
  value       = "https://${aws_cloudfront_distribution.website.domain_name}"
}
