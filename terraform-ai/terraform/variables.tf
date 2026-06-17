variable "created_by" {
  description = "GitHub actor creating the infrastructure"
  type        = string
}

variable "created_date" {
  description = "Creation date for tagging"
  type        = string
  default     = "unknown"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"
}

variable "aws_region" {
  description = "AWS region to deploy to"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance size"
  type        = string
  default     = "t3.micro"
}

variable "resource_name" {
  description = "Canonical resource name"
  type        = string
}
