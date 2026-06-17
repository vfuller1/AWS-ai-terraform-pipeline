variable "name" {
  type = string
}

variable "created_by" {
  type = string
}

variable "created_date" {
  type = string
}

variable "environment" {
  type = string
}

variable "extra_tags" {
  type    = map(string)
  default = {}
}

resource "aws_s3_bucket" "this" {
  bucket = var.name

  tags = merge(
    {
      Name        = var.name
      Owner       = var.created_by
      CreatedDate = var.created_date
      ManagedBy   = "terraform-ai"
      Environment = var.environment
    },
    var.extra_tags
  )
}

resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "bucket_name" {
  value = aws_s3_bucket.this.bucket
}

output "bucket_arn" {
  value = aws_s3_bucket.this.arn
}
