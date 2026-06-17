variable "name" {
  type = string
}

variable "instance_type" {
  type = string
}

variable "ami_id" {
  type = string
}

variable "subnet_id" {
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

resource "aws_instance" "this" {
  ami           = var.ami_id
  instance_type = var.instance_type
  subnet_id     = var.subnet_id

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

output "instance_id" {
  value = aws_instance.this.id
}

output "public_ip" {
  value = aws_instance.this.public_ip
}

output "private_ip" {
  value = aws_instance.this.private_ip
}
