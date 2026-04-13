# ===================================================================
# MiniStack Multi-Cloud — Huawei Cloud OBS Bucket Examples
# ===================================================================
#
# This directory contains Terraform configurations for working with
# Huawei Cloud Object Storage Service (OBS) buckets using MiniStack
# as the local emulator.
#
# Prerequisites:
#   1. MiniStack running: docker compose up -d
#   2. Huawei Cloud provider installed
#   3. Environment variables set (see terraform.tfvars.example)
#
# Usage:
#   terraform init
#   terraform plan
#   terraform apply
# ===================================================================

terraform {
  required_version = ">= 1.0"

  required_providers {
    huaweicloud = {
      source  = "huaweicloud/huaweicloud"
      version = ">= 1.50.0"
    }
  }
}

# ---------------------------------------------------------------------------
# Provider Configuration — Point to MiniStack local endpoint
# ---------------------------------------------------------------------------
provider "huaweicloud" {
  access_key  = var.huaweicloud_access_key
  secret_key  = var.huaweicloud_secret_key
  region      = var.huaweicloud_region
  project_id  = var.huaweicloud_project_id

  # Override endpoints to point to MiniStack local emulator
  endpoints = {
    obs = "http://localhost:4566"
  }

  # Disable version checking for faster operations
  skip_check = true
}

# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------
variable "huaweicloud_access_key" {
  description = "Huawei Cloud Access Key (AK)"
  type        = string
  default     = "test"
}

variable "huaweicloud_secret_key" {
  description = "Huawei Cloud Secret Key (SK)"
  type        = string
  default     = "test"
  sensitive   = true
}

variable "huaweicloud_region" {
  description = "Huawei Cloud region"
  type        = string
  default     = "sa-brazil-1"
}

variable "huaweicloud_project_id" {
  description = "Huawei Cloud Project ID"
  type        = string
  default     = "0000000000000000"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

# ---------------------------------------------------------------------------
# Locals
# ---------------------------------------------------------------------------
locals {
  common_tags = {
    ManagedBy   = "Terraform"
    Environment = var.environment
    Project     = "MiniStack"
    Cloud       = "Huawei"
  }
}

# ---------------------------------------------------------------------------
# Example 1: Basic OBS Bucket
# ---------------------------------------------------------------------------
resource "huaweicloud_obs_bucket" "basic" {
  bucket        = "ministack-basic-bucket-${var.environment}"
  storage_class = "STANDARD"
  acl           = "private"

  tags = merge(local.common_tags, {
    Name = "Basic OBS Bucket"
    Type = "basic"
  })
}

# ---------------------------------------------------------------------------
# Example 2: OBS Bucket with Versioning
# ---------------------------------------------------------------------------
resource "huaweicloud_obs_bucket" "versioned" {
  bucket        = "ministack-versioned-bucket-${var.environment}"
  storage_class = "STANDARD"
  acl           = "private"

  versioning = true

  tags = merge(local.common_tags, {
    Name      = "Versioned OBS Bucket"
    Type      = "versioned"
    Versioned = "true"
  })
}

# ---------------------------------------------------------------------------
# Example 3: OBS Bucket with Logging
# ---------------------------------------------------------------------------
resource "huaweicloud_obs_bucket" "logging" {
  bucket        = "ministack-logging-bucket-${var.environment}"
  storage_class = "STANDARD"
  acl           = "log-delivery-write"

  logging {
    target_bucket = huaweicloud_obs_bucket.logs_target.bucket
    target_prefix = "access-logs/"
  }

  tags = merge(local.common_tags, {
    Name = "Logging OBS Bucket"
    Type = "logging"
  })
}

# Target bucket for logs
resource "huaweicloud_obs_bucket" "logs_target" {
  bucket        = "ministack-logs-target-${var.environment}"
  storage_class = "STANDARD"
  acl           = "private"

  tags = merge(local.common_tags, {
    Name = "Logs Target Bucket"
    Type = "logs-target"
  })
}

# ---------------------------------------------------------------------------
# Example 4: OBS Bucket with Lifecycle Rules
# ---------------------------------------------------------------------------
resource "huaweicloud_obs_bucket" "lifecycle" {
  bucket        = "ministack-lifecycle-bucket-${var.environment}"
  storage_class = "STANDARD"
  acl           = "private"

  versioning = true

  lifecycle_rule {
    name    = "archive-old-logs"
    prefix  = "logs/"
    enabled = true

    expiration {
      days = 365
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    transition {
      days          = 180
      storage_class = "COLD"
    }

    noncurrent_version_expiration {
      days = 180
    }

    noncurrent_version_transition {
      days          = 60
      storage_class = "GLACIER"
    }
  }

  lifecycle_rule {
    name    = "delete-temp-uploads"
    prefix  = "tmp/"
    enabled = true

    expiration {
      days = 7
    }
  }

  tags = merge(local.common_tags, {
    Name = "Lifecycle OBS Bucket"
    Type = "lifecycle"
  })
}

# ---------------------------------------------------------------------------
# Example 5: OBS Bucket with CORS Rules
# ---------------------------------------------------------------------------
resource "huaweicloud_obs_bucket" "cors" {
  bucket        = "ministack-cors-bucket-${var.environment}"
  storage_class = "STANDARD"
  acl           = "public-read"

  cors_rule {
    allowed_origins = ["https://example.com", "https://app.example.com"]
    allowed_methods = ["GET", "POST", "PUT", "HEAD", "DELETE"]
    allowed_headers = ["Authorization", "Content-Type", "X-Requested-With"]
    max_age_seconds = 3600
    expose_headers  = ["ETag", "x-obs-request-id"]
  }

  cors_rule {
    allowed_origins = ["*"]
    allowed_methods = ["GET", "HEAD"]
    max_age_seconds = 86400
  }

  tags = merge(local.common_tags, {
    Name = "CORS OBS Bucket"
    Type = "cors"
  })
}

# ---------------------------------------------------------------------------
# Example 6: OBS Bucket with Website Hosting
# ---------------------------------------------------------------------------
resource "huaweicloud_obs_bucket" "website" {
  bucket        = "ministack-website-bucket-${var.environment}"
  storage_class = "STANDARD"
  acl           = "public-read"

  website {
    index_document = "index.html"
    error_document = "error.html"
  }

  tags = merge(local.common_tags, {
    Name = "Website OBS Bucket"
    Type = "website"
  })
}

# ---------------------------------------------------------------------------
# Example 7: OBS Bucket with Server-Side Encryption
# ---------------------------------------------------------------------------
resource "huaweicloud_obs_bucket" "encrypted" {
  bucket        = "ministack-encrypted-bucket-${var.environment}"
  storage_class = "STANDARD"
  acl           = "private"

  server_side_encryption {
    algorithm  = "kms"
    kms_key_id = huaweicloud_kms_key_v1.main.id
  }

  tags = merge(local.common_tags, {
    Name      = "Encrypted OBS Bucket"
    Type      = "encrypted"
    Encrypted = "true"
  })
}

# KMS Key for encryption
resource "huaweicloud_kms_key_v1" "main" {
  key_alias    = "ministack-obs-encryption-key"
  key_description = "KMS key for OBS bucket encryption"
  is_enabled   = true

  tags = merge(local.common_tags, {
    Name = "OBS Encryption Key"
  })
}

# ---------------------------------------------------------------------------
# Example 8: OBS Bucket Object Upload
# ---------------------------------------------------------------------------
resource "huaweicloud_obs_bucket_object" "index_html" {
  bucket       = huaweicloud_obs_bucket.website.bucket
  key          = "index.html"
  content      = <<-EOF
    <!DOCTYPE html>
    <html>
    <head>
      <title>MiniStack OBS Website</title>
    </head>
    <body>
      <h1>Hello from MiniStack OBS Bucket!</h1>
      <p>This is a static website hosted on Huawei Cloud OBS.</p>
    </body>
    </html>
  EOF
  content_type = "text/html"
  acl          = "public-read"
}

resource "huaweicloud_obs_bucket_object" "error_html" {
  bucket       = huaweicloud_obs_bucket.website.bucket
  key          = "error.html"
  content      = <<-EOF
    <!DOCTYPE html>
    <html>
    <head>
      <title>404 - Not Found</title>
    </head>
    <body>
      <h1>404 - Page Not Found</h1>
      <p>The requested page could not be found.</p>
    </body>
    </html>
  EOF
  content_type = "text/html"
  acl          = "public-read"
}

# ---------------------------------------------------------------------------
# Example 9: OBS Bucket with Policy
# ---------------------------------------------------------------------------
resource "huaweicloud_obs_bucket_policy" "read_only" {
  bucket = huaweicloud_obs_bucket.basic.bucket
  policy = <<-EOF
    {
      "Version": "2008-10-17",
      "Statement": [
        {
          "Sid": "PublicReadForStaticAssets",
          "Effect": "Allow",
          "Principal": {
            "AWS": ["*"]
          },
          "Action": [
            "obs:GetObject",
            "obs:GetObjectVersion"
          ],
          "Resource": "${huaweicloud_obs_bucket.basic.bucket_arn}/static/*"
        }
      ]
    }
  EOF
}

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------
output "bucket_names" {
  description = "Names of all created OBS buckets"
  value = {
    basic     = huaweicloud_obs_bucket.basic.bucket
    versioned = huaweicloud_obs_bucket.versioned.bucket
    logging   = huaweicloud_obs_bucket.logging.bucket
    logs_target = huaweicloud_obs_bucket.logs_target.bucket
    lifecycle = huaweicloud_obs_bucket.lifecycle.bucket
    cors      = huaweicloud_obs_bucket.cors.bucket
    website   = huaweicloud_obs_bucket.website.bucket
    encrypted = huaweicloud_obs_bucket.encrypted.bucket
  }
}

output "bucket_domains" {
  description = "Domain names of all created OBS buckets"
  value = {
    basic     = huaweicloud_obs_bucket.basic.bucket_domain_name
    versioned = huaweicloud_obs_bucket.versioned.bucket_domain_name
    logging   = huaweicloud_obs_bucket.logging.bucket_domain_name
    lifecycle = huaweicloud_obs_bucket.lifecycle.bucket_domain_name
    cors      = huaweicloud_obs_bucket.cors.bucket_domain_name
    website   = huaweicloud_obs_bucket.website.bucket_domain_name
    encrypted = huaweicloud_obs_bucket.encrypted.bucket_domain_name
  }
}

output "website_endpoint" {
  description = "Website endpoint URL"
  value       = huaweicloud_obs_bucket.website.website_endpoint
}

output "kms_key_id" {
  description = "KMS key ID for encryption"
  value       = huaweicloud_kms_key_v1.main.id
}
