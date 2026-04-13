# Terraform Examples for Huawei Cloud OBS

This directory contains Terraform configurations for working with **Huawei Cloud Object Storage Service (OBS)** using **MiniStack** as the local emulator.

## 📁 Directory Structure

```
examples/terraform/
├── obs-simple/              # Minimal example — single bucket + object
│   └── main.tf
├── obs-bucket/              # Comprehensive example — 8 bucket configurations
│   └── main.tf
└── modules/
    └── obs-bucket/          # Reusable OBS bucket module
        └── main.tf
```

## 🚀 Quick Start

### Prerequisites

1. **MiniStack running locally:**
   ```bash
   docker compose up -d
   ```

2. **Install Terraform:**
   ```bash
   # Linux
   sudo apt-get update && sudo apt-get install -y gnupg software-properties-common
   wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg
   echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
   sudo apt-get update && sudo apt-get install terraform
   ```

3. **Install Huawei Cloud provider:**
   ```bash
   # Already included in Terraform configs — runs automatically on init
   ```

### Example 1: Simple OBS Bucket

Create a basic bucket with a sample object:

```bash
cd examples/terraform/obs-simple

terraform init
terraform plan
terraform apply -auto-approve
```

**Expected output:**
```
bucket_name = "ministack-my-bucket"
bucket_domain = "ministack-my-bucket.obs.sa-brazil-1.myhuaweicloud.com"
object_url = "https://ministack-my-bucket.obs.sa-brazil-1.myhuaweicloud.com/hello.txt"
```

### Example 2: Comprehensive OBS Configuration

Create 8 different buckets demonstrating various OBS features:

```bash
cd examples/terraform/obs-bucket

terraform init
terraform plan
terraform apply -auto-approve
```

**This creates:**
| Bucket | Feature Demonstrated |
|--------|---------------------|
| `ministack-basic-bucket-dev` | Basic private bucket |
| `ministack-versioned-bucket-dev` | Object versioning |
| `ministack-logging-bucket-dev` | Access logging |
| `ministack-logs-target-dev` | Log storage target |
| `ministack-lifecycle-bucket-dev` | Lifecycle rules (transitions + expirations) |
| `ministack-cors-bucket-dev` | CORS rules for web apps |
| `ministack-website-bucket-dev` | Static website hosting |
| `ministack-encrypted-bucket-dev` | Server-side KMS encryption |

**Plus:**
- KMS encryption key
- Sample website objects (`index.html`, `error.html`)
- Bucket policy for public read access

### Using the Reusable Module

```hcl
module "my_bucket" {
  source = "./modules/obs-bucket"

  bucket_name       = "my-app-bucket"
  storage_class     = "STANDARD"
  acl               = "private"
  enable_versioning = true

  cors_rules = [
    {
      allowed_origins = ["https://myapp.com"]
      allowed_methods = ["GET", "POST", "PUT"]
      allowed_headers = ["Authorization", "Content-Type"]
      max_age_seconds = 3600
      expose_headers  = ["ETag"]
    }
  ]

  lifecycle_rules = [
    {
      name                = "archive-old-data"
      prefix              = "data/"
      enabled             = true
      expiration_days     = 365
      transition_days     = 90
      transition_class    = "GLACIER"
      noncurrent_days     = 180
      noncurrent_class    = "GLACIER"
    }
  ]

  tags = {
    Environment = "production"
    Team        = "backend"
  }
}
```

## 🔧 Configuration

### Provider Settings

All examples point to MiniStack's local endpoint:

```hcl
provider "huaweicloud" {
  access_key = "test"                    # Default MiniStack AK
  secret_key = "test"                    # Default MiniStack SK
  region     = "sa-brazil-1"            # Any region works
  project_id = "0000000000000000"       # Default MiniStack project ID

  endpoints = {
    obs = "http://localhost:4566"       # MiniStack endpoint
  }

  skip_check = true                      # Skip provider version check
}
```

### Environment Variables (Optional)

Create a `terraform.tfvars` file:

```hcl
huaweicloud_access_key = "your-custom-ak"
huaweicloud_secret_key = "your-custom-sk"
huaweicloud_region     = "cn-south-1"
huaweicloud_project_id = "your-project-id"
environment            = "production"
```

## 📊 OBS Bucket Features Demonstrated

| Feature | Resource | Description |
|---------|----------|-------------|
| **Basic Bucket** | `huaweicloud_obs_bucket` | Create bucket with storage class and ACL |
| **Versioning** | `versioning = true` | Enable object version tracking |
| **Logging** | `logging {}` block | Configure access log delivery |
| **Lifecycle** | `lifecycle_rule {}` block | Auto-transition and expire objects |
| **CORS** | `cors_rule {}` block | Cross-origin resource sharing rules |
| **Website** | `website {}` block | Static website hosting configuration |
| **Encryption** | `server_side_encryption {}` block | KMS server-side encryption |
| **Objects** | `huaweicloud_obs_bucket_object` | Upload files to buckets |
| **Policies** | `huaweicloud_obs_bucket_policy` | Bucket access policies |
| **Tags** | `tags = {}` | Resource tagging and organization |

## 🧪 Verify with MiniStack

After applying, verify the buckets were created:

```bash
# Check Huawei health endpoint
curl http://localhost:4566/_huawei/health | jq

# List all OBS buckets
curl -X GET \
  -H "Host: obs.localhost:4566" \
  http://localhost:4566/

# Access uploaded object
curl http://localhost:4566/ministack-my-bucket/hello.txt
```

## 🧹 Cleanup

Destroy all created resources:

```bash
terraform destroy -auto-approve
```

## 🔗 References

- [MiniStack Documentation](../../../README.md)
- [Huawei Cloud OBS Provider](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/obs_bucket)
- [Huawei Cloud OBS API](https://support.huaweicloud.com/intl/en-us/api-obs/obs_04_0039.html)
- [Terraform OBS Resources](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/obs_bucket)

## ⚠️ Notes

- These examples are designed to work with **MiniStack as a local emulator**, not with real Huawei Cloud
- To use with real Huawei Cloud, remove the `endpoints` override and configure real credentials
- All bucket names include environment suffix to avoid conflicts
- Storage classes: `STANDARD`, `WARM`, `COLD`, `GLACIER`
- ACL options: `private`, `public-read`, `public-read-write`, `log-delivery-write`
