# Multi-Cloud Operations

## Overview

MiniStack can run **AWS, Azure, Huawei Cloud, and GCP** simultaneously on a single port (`4566`). The `detect_provider()` function in `core/router.py` automatically routes each request to the correct cloud based on headers and URL paths.

## Cloud Mode

Set `CLOUD_MODE` to control which clouds are active:

| Value | Behavior |
|-------|----------|
| `all` (default) | All 4 clouds active — auto-detected per request |
| `aws` | AWS services only (original MiniStack behavior) |
| `azure` | Azure services only |
| `huawei` | Huawei Cloud services only |
| `gcp` | GCP services only |

### Setting Cloud Mode

```bash
# Environment variable
export CLOUD_MODE=all

# Docker
docker run -p 4566:4566 -e CLOUD_MODE=all ministackorg/ministack

# Docker Compose
# (edit docker-compose.yml environment section)
```

## Provider Detection

The router detects the target cloud by examining request headers and paths:

### GCP Signals
- **Headers:** `x-goog-api-client`, `x-goog-user-project`, `x-goog-request-params`, `x-goog-api-key`
- **Paths:** `/storage/v1/`, `/pubsub/v1/`, `/cloudfunctions/v`, `/bigquery/v`, `/sql/v`, `/run/v`, `/logging/v`, `/computeMetadata/`, `/v1/projects/`, `/v1beta1/projects/`, `/v2/projects/`

### Azure Signals
- **Headers:** `x-ms-date`, `x-ms-client-request-id`, `x-ms-version`, `Authorization: Bearer ...`, `Authorization: SharedKey ...`
- **Paths:** `/subscriptions/`, `/tenant/`, `/keyvault/`, `/azure/`, `/api/`, `/providers/Microsoft.`, `oauth2/v2.0`, `/.default`

### Huawei Cloud Signals
- **Headers:** `x-auth-token`, `x-sdk-date`, `Authorization: SDK-HMAC-SHA256 ...`, `Authorization: Huawei4-HMAC-SHA256 ...`
- **Paths:** `/v3/auth/`, `/v1.0/`, `/v2/` (except `/v2/apis`), `/v3/`

### AWS (Default)
- Everything else falls through to AWS detection (X-Amz-Target, AWS4-HMAC-SHA256, Action query params, etc.)

## Starting Multiple Clouds

### All Clouds

```bash
./bin/ministack-start
# or
make start-all
```

### Specific Clouds

```bash
# AWS + Azure
./bin/ministack-start aws,azure

# Azure + GCP
./bin/ministack-start azure,gcp

# All except AWS
./bin/ministack-start azure,huawei,gcp
```

## Health Checks

```bash
# Individual clouds
curl http://localhost:4566/_ministack/health    # AWS
curl http://localhost:4566/_azure/health         # Azure
curl http://localhost:4566/_huawei/health        # Huawei Cloud
curl http://localhost:4566/_gcp/health           # GCP

# Consolidated (all clouds)
curl http://localhost:4566/_multicloud/health
```

Response:
```json
{
  "cloud_mode": "all",
  "aws_services": 41,
  "azure_services": 30,
  "huawei_services": 17,
  "gcp_services": 14,
  "status": "available"
}
```

## Reset Individual Clouds

```bash
# Reset specific cloud
curl -X POST http://localhost:4566/_ministack/reset   # AWS
curl -X POST http://localhost:4566/_azure/reset        # Azure
curl -X POST http://localhost:4566/_huawei/reset       # Huawei Cloud
curl -X POST http://localhost:4566/_gcp/reset          # GCP
```

## Stopping Multiple Clouds

```bash
# Stop all
./bin/ministack-stop
# or
make stop-all

# Stop specific clouds
./bin/ministack-stop aws,azure
```

## Cross-Cloud Scenarios

### Multi-Cloud Application

```python
# Python example: use AWS S3 + Azure Blob + GCP GCS in one app
import boto3
import requests

# AWS S3
s3 = boto3.client("s3", endpoint_url="http://localhost:4566",
                   aws_access_key_id="test", aws_secret_access_key="test")
s3.create_bucket(Bucket="aws-bucket")

# Azure Blob
requests.put("http://localhost:4566/azure/blob/devstoreaccount1/azure-container?restype=container",
             headers={"Authorization": "Bearer test"})

# GCP GCS
requests.post("http://localhost:4566/storage/v1/b",
              json={"name": "gcp-bucket"},
              headers={"x-goog-api-client": "test"})
```

### Testing All Clouds

```bash
# Run all cloud test suites
pytest tests/ -v

# Run per-cloud
pytest tests/test_s3.py -v                    # AWS
pytest tests/test_azure_services.py -v         # Azure
pytest tests/test_huawei_services.py -v        # Huawei Cloud
pytest tests/test_gcp_services.py -v           # GCP
```

## Environment Variables Summary

| Variable | Default | Cloud | Description |
|----------|---------|-------|-------------|
| `CLOUD_MODE` | `all` | All | `aws`/`azure`/`huawei`/`gcp`/`all` |
| `MINISTACK_ACCOUNT_ID` | `000000000000` | AWS | Default AWS account ID |
| `MINISTACK_REGION` | `us-east-1` | AWS | Default AWS region |
| `AZURE_TENANT_ID` | `0000...0000` | Azure | Azure tenant ID |
| `AZURE_SUBSCRIPTION_ID` | `0000...0001` | Azure | Azure subscription ID |
| `AZURE_CLIENT_ID` | `test` | Azure | Service principal ID |
| `AZURE_CLIENT_SECRET` | `test` | Azure | Service principal secret |
| `HUAWEICLOUD_SDK_AK` | `test` | Huawei | Access Key |
| `HUAWEICLOUD_SDK_SK` | `test` | Huawei | Secret Key |
| `HUAWEICLOUD_PROJECT_ID` | `0000000000000000` | Huawei | Project ID |
| `HUAWEICLOUD_REGION` | `cn-north-4` | Huawei | Region |
| `GCP_PROJECT_ID` | `ministack-emulator` | GCP | GCP Project ID |
| `GCP_REGION` | `us-central1` | GCP | Default region |
| `GCP_ZONE` | `us-central1-a` | GCP | Default zone |

## Resource Isolation

Each cloud maintains completely separate state:

- **AWS:** Uses `AccountScopedDict` with 12-digit numeric access keys
- **Azure:** Uses `AccountScopedDict` with subscription/tenant IDs
- **Huawei Cloud:** Uses `AccountScopedDict` with project IDs
- **GCP:** Uses `AccountScopedDict` with project IDs

No resource collisions between clouds — same-name resources in different clouds are fully isolated.
