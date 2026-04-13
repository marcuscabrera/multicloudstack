# ===================================================================
# MiniStack — Huawei Cloud OBS Bucket (Simple Example)
# ===================================================================
#
# A minimal Terraform configuration for creating a single OBS bucket
# using MiniStack as the local emulator.
#
# Quick start:
#   terraform init && terraform apply -auto-approve
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

provider "huaweicloud" {
  access_key = "test"
  secret_key = "test"
  region     = "sa-brazil-1"
  project_id = "0000000000000000"

  endpoints = {
    obs = "http://localhost:4566"
  }

  skip_check = true
}

# Basic OBS Bucket
resource "huaweicloud_obs_bucket" "this" {
  bucket        = "ministack-my-bucket"
  storage_class = "STANDARD"
  acl           = "private"

  tags = {
    Name    = "My OBS Bucket"
    Managed = "Terraform"
  }
}

# Upload a sample object
resource "huaweicloud_obs_bucket_object" "sample" {
  bucket  = huaweicloud_obs_bucket.this.bucket
  key     = "hello.txt"
  content = "Hello from MiniStack OBS!"

  tags = {
    Environment = "dev"
  }
}

output "bucket_name" {
  value = huaweicloud_obs_bucket.this.bucket
}

output "bucket_domain" {
  value = huaweicloud_obs_bucket.this.bucket_domain_name
}

output "object_url" {
  value = "https://${huaweicloud_obs_bucket.this.bucket_domain_name}/hello.txt"
}
