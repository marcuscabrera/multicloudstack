# MiniStack for Huawei Cloud

Local emulator for **Huawei Cloud** services, built on the MiniStack architecture.
Emulates 17 Huawei Cloud services on a single port (`4566`), compatible with
the official `huaweicloudsdkcore` Python SDK and Terraform provider `huaweicloud`.

## Quick Start

### Docker (Huawei Mode Only)

```bash
docker compose -f docker-compose.huawei.yml up -d --build
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HUAWEI_MODE` | `0` | `0` = AWS only, `1` = Huawei only, `2` = Hybrid (both) |
| `HUAWEICLOUD_SDK_AK` | `test` | Access Key for emulated authentication |
| `HUAWEICLOUD_SDK_SK` | `test` | Secret Key for emulated authentication |
| `HUAWEICLOUD_PROJECT_ID` | `0000000000000000` | Default project ID |
| `HUAWEICLOUD_REGION` | `cn-north-4` | Default region |
| `GATEWAY_PORT` | `4566` | Gateway port (shared with AWS mode) |

### Python SDK Usage

```python
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcore.http.http_config import HttpConfig
from huaweicloudsdkobs.v1.region.obs_region import ObsRegion
from huaweicloudsdkobs.v1 import ObsClient, ListBucketsRequest

credentials = BasicCredentials(
    ak="test",
    sk="test",
    project_id="0000000000000000"
)

http_config = HttpConfig()
http_config.endpoint_override = "http://localhost:4566"

client = ObsClient.new_builder() \
    .with_credentials(credentials) \
    .with_region(ObsRegion.value_of("cn-north-4")) \
    .with_http_config(http_config) \
    .build()

# List buckets (works against the emulator)
response = client.list_buckets(ListBucketsRequest())
print(response.buckets)
```

### Using with huaweicloudsdkcore (raw HTTP)

```python
import requests

ENDPOINT = "http://localhost:4566"
PROJECT_ID = "0000000000000000"

# 1. Get IAM token
resp = requests.post(
    f"{ENDPOINT}/v3/auth/tokens",
    json={"auth": {"methods": ["token"]}},
    headers={"Content-Type": "application/json"}
)
token = resp.headers.get("X-Subject-Token")

# 2. Create an OBS bucket
resp = requests.put(
    f"{ENDPOINT}/v1/my-bucket",
    headers={"X-Auth-Token": token}
)
print(resp.status_code)  # 200

# 3. Create a FunctionGraph function
resp = requests.post(
    f"{ENDPOINT}/v2/{PROJECT_ID}/fgs/functions",
    json={
        "func_name": "hello-world",
        "runtime": "Python3.9",
        "handler": "index.handler",
        "memory_size": 256,
    },
    headers={"Content-Type": "application/json"}
)
print(resp.json())
```

## Supported Services

### Priority Services (Full Implementation)

| Huawei Cloud Service | AWS Equivalent | API Path | Status |
|---------------------|----------------|----------|--------|
| **OBS** (Object Storage) | S3 | `/v1/{bucket}/...` | ✅ Full (S3-compatible) |
| **IAM** | IAM/STS | `/v3/auth/tokens` | ✅ Token auth |
| **SMN** (Simple Message Notification) | SNS | `/v2/{proj}/notifications/...` | ✅ Topic CRUD, Publish, Subscribe |
| **FunctionGraph** | Lambda | `/v2/{proj}/fgs/functions/...` | ✅ CRUD, Invoke, Versions, Aliases |
| **RDS** | RDS | `/v3/{proj}/instances` | ✅ Instance CRUD, Actions |
| **DCS** (Distributed Cache) | ElastiCache | `/v2/{proj}/instances` | ✅ Instance CRUD, Modify |
| **LTS** (Log Tank Service) | CloudWatch Logs | `/v2/{proj}/groups`, `/streams`, `/logs` | ✅ Groups, Streams, Log push/query |
| **VPC** | VPC/EC2 Networking | `/v1/{proj}/vpcs`, `/subnets`, `/security-groups` | ✅ VPC, Subnet, SG CRUD |

### Extended Services (Stub Implementation)

| Service | API Path | Description |
|---------|----------|-------------|
| **DMS** (Distributed Message) | `/v1.0/{proj}/queues` | Queue CRUD (SQS-compatible) |
| **AOM** (App Ops Management) | `/v1/{proj}/ams/metrics` | Metric submission/query |
| **ECS** (Elastic Cloud Server) | `/v1/{proj}/cloudservers` | Server CRUD |
| **APIG** (API Gateway) | `/v2/{proj}/apigw/instances` | API gateway instances |
| **DIS** (Data Ingestion) | `/v2/{proj}/streams` | Stream CRUD (Kinesis-compatible) |
| **KMS** | `/v1.0/{proj}/kms/keys` | Key CRUD |
| **CSMS** (Cloud Secret Management) | `/v1/{proj}/secrets` | Secret CRUD |
| **CCE** (Cloud Container Engine) | `/api/v3/{proj}/clusters` | Kubernetes-style cluster CRUD |
| **RFS** (Resource Formation) | `/v1/{proj}/stacks` | Stack CRUD (CloudFormation-compatible) |

## Admin Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/_huawei/health` | GET | Health check with all Huawei service statuses |
| `/_huawei/reset` | POST | Reset all Huawei service state |
| `/_ministack/health` | GET | Combined AWS + Huawei health (in hybrid mode) |
| `/_ministack/reset` | POST | Reset all state (AWS + Huawei) |

## Authentication

### IAM Token Flow

1. **Request a token:**
   ```
   POST /v3/auth/tokens
   {"auth": {"methods": ["token"], "scope": {"project": {"id": "..."}}}}
   ```
2. **Receive token in header:**
   ```
   X-Subject-Token: <token-id>
   ```
3. **Use token for subsequent requests:**
   ```
   X-Auth-Token: <token-id>
   ```

### AK/SK Signature (Huawei SDK)

The emulator supports Huawei's `Huawei4-HMAC-SHA256` signature scheme.
When using the official SDK, configure the endpoint override:

```python
http_config.endpoint_override = "http://localhost:4566"
```

The signature verification is performed in `ministack/core/auth_huawei.py`.

## Terraform Provider Compatibility

Works with the `huaweicloud` Terraform provider. Configure the provider:

```hcl
provider "huaweicloud" {
  region     = "cn-north-4"
  access_key = "test"
  secret_key = "test"

  endpoints {
    obs        = "http://localhost:4566"
    iam        = "http://localhost:4566"
    smn        = "http://localhost:4566"
    fgs        = "http://localhost:4566"
    rds        = "http://localhost:4566"
    dcs        = "http://localhost:4566"
    lts        = "http://localhost:4566"
    vpc        = "http://localhost:4566"
  }
}
```

## Running Tests

```bash
# Set Huawei mode
export HUAWEI_MODE=1

# Run the server
python -m uvicorn ministack.app:app --host 0.0.0.0 --port 4566 &

# Run Huawei tests
pytest tests/test_huawei_services.py -v
```

## Architecture

```
ministack/
├── core/
│   ├── auth_huawei.py      # AK/SK signature verification, IAM tokens
│   └── router.py           # Dual-mode routing (AWS ↔ Huawei)
├── services/
│   ├── obs.py              # OBS (reuses S3)
│   ├── iam_hw.py           # IAM token authentication
│   ├── smn.py              # Simple Message Notification
│   ├── functiongraph.py    # FunctionGraph (reuses lambda_runtime)
│   ├── rds_hw.py           # RDS Huawei
│   ├── dcs.py              # Distributed Cache Service
│   ├── lts.py              # Log Tank Service
│   ├── vpc_hw.py           # VPC Huawei
│   ├── huawei_extended.py  # DMS, AOM, ECS, APIG, DIS, KMS, CSMS, CCE, RFS
│   └── {dms,aom,ecs_hw,apig,dis,kms_hw,csms,cce,rfs}.py  # Thin wrappers
└── app.py                  # ASGI app with Huawei handler registration
```

## Dual Mode Operation

| Mode | `HUAWEI_MODE` | Behavior |
|------|---------------|----------|
| AWS only | `0` (default) | Only AWS service detection active |
| Huawei only | `1` | All requests routed to Huawei services |
| Hybrid | `2` | Both AWS and Huawei detection active; Huawei headers take precedence |

## Differences from Real Huawei Cloud

- All services are **in-memory** emulators (no persistent infrastructure)
- RDS/DCS return **emulated endpoints** (not real containers unless Docker integration is added)
- Authentication uses **simplified AK/SK** (default: `test`/`test`)
- IAM tokens are **not cryptographically signed** (emulated only)
- No **billing, quotas, or rate limiting**
- No **real networking** (all endpoints are localhost)

## License

MIT — same as MiniStack upstream.
