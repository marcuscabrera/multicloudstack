# Getting Started

## Prerequisites

- **Docker** (for containerized deployment) or **Python 3.10+** (for direct execution)
- **Docker Compose** (for multi-service deployments)
- `curl` (for health checks)

## Installation

### Option 1: Docker (Recommended)

```bash
git clone https://github.com/ministackorg/ministack-huawei.git
cd ministack-huawei
```

### Option 2: Python Package

```bash
pip install -e .
# or
pip install -e ".[full]"  # With real infrastructure support
```

### Option 3: From Source

```bash
pip install -r requirements.txt
```

## Quick Start

### Start All Clouds

```bash
# Using shell script
./bin/ministack-start

# Using Make
make start-all

# Using Docker Compose directly
docker compose up -d --build
```

### Start Individual Clouds

```bash
# AWS only
./bin/ministack-start aws

# Azure only
./bin/ministack-start azure

# Huawei Cloud only
./bin/ministack-start huawei

# GCP only
./bin/ministack-start gcp

# Multiple clouds
./bin/ministack-start aws,azure,gcp
```

### Verify Installation

```bash
# AWS health
curl -s http://localhost:4566/_ministack/health | python3 -m json.tool

# Azure health
curl -s http://localhost:4566/_azure/health | python3 -m json.tool

# Huawei Cloud health
curl -s http://localhost:4566/_huawei/health | python3 -m json.tool

# GCP health
curl -s http://localhost:4566/_gcp/health | python3 -m json.tool

# Multi-cloud consolidated
curl -s http://localhost:4566/_multicloud/health | python3 -m json.tool
```

### Stop All Clouds

```bash
# Using shell script
./bin/ministack-stop

# Using Make
make stop-all

# Using Docker Compose
docker compose down
```

## First Tests

### AWS

```bash
# Using awslocal wrapper
./bin/awslocal s3 mb s3://test-bucket
./bin/awslocal s3 ls

# Using AWS CLI directly
aws --endpoint-url=http://localhost:4566 s3 mb s3://test-bucket
```

### Azure

```bash
# Create blob container
curl -X PUT "http://localhost:4566/azure/blob/devstoreaccount1/mycontainer?restype=container" \
  -H "Authorization: Bearer test"

# List containers
curl "http://localhost:4566/azure/blob/devstoreaccount1" \
  -H "Authorization: Bearer test"
```

### Huawei Cloud

```bash
# Get IAM token
curl -X POST "http://localhost:4566/v3/auth/tokens" \
  -d "grant_type=client_credentials&client_id=test&client_secret=test" \
  -H "Content-Type: application/x-www-form-urlencoded"
```

### GCP

```bash
# Metadata server
curl http://localhost:4566/computeMetadata/v1/project/project-id

# Create bucket
curl -X POST http://localhost:4566/storage/v1/b \
  -H "x-goog-api-client: test" \
  -d '{"name": "my-gcp-bucket"}'
```

## Environment Variables

### Core

| Variable | Default | Description |
|----------|---------|-------------|
| `GATEWAY_PORT` | `4566` | Port for all clouds |
| `CLOUD_MODE` | `all` | `aws` / `azure` / `huawei` / `gcp` / `all` |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### AWS

| Variable | Default | Description |
|----------|---------|-------------|
| `MINISTACK_ACCOUNT_ID` | `000000000000` | Default AWS account ID |
| `MINISTACK_REGION` | `us-east-1` | Default AWS region |

### Azure

| Variable | Default | Description |
|----------|---------|-------------|
| `AZURE_TENANT_ID` | `0000...0000` | Azure tenant ID |
| `AZURE_SUBSCRIPTION_ID` | `0000...0001` | Azure subscription ID |
| `AZURE_LOCATION` | `eastus` | Default Azure region |
| `AZURE_CLIENT_ID` | `test` | Service principal client ID |
| `AZURE_CLIENT_SECRET` | `test` | Service principal secret |

### Huawei Cloud

| Variable | Default | Description |
|----------|---------|-------------|
| `HUAWEICLOUD_SDK_AK` | `test` | Access Key |
| `HUAWEICLOUD_SDK_SK` | `test` | Secret Key |
| `HUAWEICLOUD_PROJECT_ID` | `0000000000000000` | Project ID |
| `HUAWEICLOUD_REGION` | `cn-north-4` | Region |

### GCP

| Variable | Default | Description |
|----------|---------|-------------|
| `GCP_PROJECT_ID` | `ministack-emulator` | GCP Project ID |
| `GCP_REGION` | `us-central1` | Default region |
| `GCP_ZONE` | `us-central1-a` | Default zone |

## Next Steps

- [AWS Services](aws.md) — 41 services including S3, SQS, Lambda, RDS
- [Azure Services](azure.md) — 30 services including Blob Storage, Entra ID, Cosmos DB
- [Huawei Cloud](huawei.md) — 17 services including OBS, SMN, FunctionGraph
- [GCP Services](gcp.md) — 14 services including GCS, Pub/Sub, BigQuery
- [Multi-Cloud Operations](multi-cloud.md) — Provider detection, CLOUD_MODE management
- [API Reference](api-reference.md) — All internal and external endpoints
- [Troubleshooting](troubleshooting.md) — Common issues and solutions
