# ===================================================================
# MiniStack — Reusable OBS Bucket Module
# ===================================================================

variable "bucket_name" {
  description = "Name of the OBS bucket"
  type        = string
}

variable "storage_class" {
  description = "Storage class: STANDARD, WARM, COLD, GLACIER"
  type        = string
  default     = "STANDARD"
}

variable "acl" {
  description = "Bucket ACL: private, public-read, public-read-write, log-delivery-write"
  type        = string
  default     = "private"
}

variable "enable_versioning" {
  description = "Enable object versioning"
  type        = bool
  default     = false
}

variable "enable_logging" {
  description = "Enable access logging"
  type        = bool
  default     = false
}

variable "log_target_bucket" {
  description = "Target bucket for access logs"
  type        = string
  default     = null
}

variable "log_prefix" {
  description = "Prefix for log objects"
  type        = string
  default     = "logs/"
}

variable "cors_rules" {
  description = "CORS rules configuration"
  type = list(object({
    allowed_origins = list(string)
    allowed_methods = list(string)
    allowed_headers = list(string)
    max_age_seconds = number
    expose_headers  = list(string)
  }))
  default = []
}

variable "lifecycle_rules" {
  description = "Lifecycle rules configuration"
  type = list(object({
    name                = string
    prefix              = string
    enabled             = bool
    expiration_days     = number
    transition_days     = number
    transition_class    = string
    noncurrent_days     = number
    noncurrent_class    = string
  }))
  default = []
}

variable "tags" {
  description = "Tags to apply to the bucket"
  type        = map(string)
  default     = {}
}

# ---------------------------------------------------------------------------
# OBS Bucket Resource
# ---------------------------------------------------------------------------
resource "huaweicloud_obs_bucket" "this" {
  bucket        = var.bucket_name
  storage_class = var.storage_class
  acl           = var.acl

  versioning = var.enable_versioning

  dynamic "logging" {
    for_each = var.enable_logging && var.log_target_bucket != null ? [1] : []
    content {
      target_bucket = var.log_target_bucket
      target_prefix = var.log_prefix
    }
  }

  dynamic "cors_rule" {
    for_each = var.cors_rules
    content {
      allowed_origins = cors_rule.value.allowed_origins
      allowed_methods = cors_rule.value.allowed_methods
      allowed_headers = cors_rule.value.allowed_headers
      max_age_seconds = cors_rule.value.max_age_seconds
      expose_headers  = cors_rule.value.expose_headers
    }
  }

  dynamic "lifecycle_rule" {
    for_each = var.lifecycle_rules
    content {
      name    = lifecycle_rule.value.name
      prefix  = lifecycle_rule.value.prefix
      enabled = lifecycle_rule.value.enabled

      expiration {
        days = lifecycle_rule.value.expiration_days
      }

      transition {
        days          = lifecycle_rule.value.transition_days
        storage_class = lifecycle_rule.value.transition_class
      }

      noncurrent_version_expiration {
        days = lifecycle_rule.value.noncurrent_days
      }

      noncurrent_version_transition {
        days          = lifecycle_rule.value.noncurrent_days
        storage_class = lifecycle_rule.value.noncurrent_class
      }
    }
  }

  tags = var.tags
}

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------
output "bucket_id" {
  description = "Bucket ID"
  value       = huaweicloud_obs_bucket.this.id
}

output "bucket_name" {
  description = "Bucket name"
  value       = huaweicloud_obs_bucket.this.bucket
}

output "bucket_domain" {
  description = "Bucket domain name"
  value       = huaweicloud_obs_bucket.this.bucket_domain_name
}

output "bucket_arn" {
  description = "Bucket ARN"
  value       = huaweicloud_obs_bucket.this.bucket_arn
}

output "storage_class" {
  description = "Storage class"
  value       = huaweicloud_obs_bucket.this.storage_class
}
