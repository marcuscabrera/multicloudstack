# MiniStack — Multi-Cloud Local Emulator

## Project Overview

**MiniStack** is a free, open-source **multi-cloud local emulator** (MIT licensed, v1.2.5) that emulates **102 services across 4 cloud providers** on a single port (default `4566`):

| Cloud | Services | Key Examples |
|-------|----------|-------------|
| **AWS** | 56 | S3, SQS, SNS, DynamoDB, Lambda, IAM, STS, RDS, EC2, ECS, CloudFormation |
| **Azure** | 29 | Blob Storage, Entra ID, Service Bus, Functions, Cosmos DB, Key Vault, ARM |
| **Huawei Cloud** | 17 | OBS, IAM, SMN, FunctionGraph, RDS, DCS, LTS, VPC |
| **GCP** | 14 | GCS, Pub/Sub, Cloud Functions, BigQuery, Cloud SQL, Secret Manager, KMS |

### Key Differentiators
- **~300MB Docker image**, ~50MB RAM at idle (vs LocalStack's ~1GB / ~500MB RAM)
- **Fast startup** — under 2 seconds
- **Real infrastructure** — RDS/Azure SQL/Huawei RDS spin up actual Postgres/MySQL containers; Redis for all clouds; Athena runs real SQL via DuckDB; ECS runs real Docker containers
- **Multi-tenancy** via 12-digit numeric AWS access keys acting as Account IDs
- **Drop-in compatible** with `boto3`, `azure-sdk-for-python`, `huaweicloudsdkcore`, Terraform, CDK, Pulumi
- **Interactive dashboard** at `http://localhost:4566/dashboard`

### Architecture
- **Single-port ASGI** server (Uvicorn) on port 4566
- **Multi-cloud router** (`detect_provider()`) auto-detects AWS/Azure/Huawei/GCP per request based on headers and URL paths
- Each service is an independent Python module with `async handle_request()` and `reset()` functions
- **`AccountScopedDict`** namespaces all state per account for multi-tenancy
- **Warm Lambda workers** — persistent subprocess workers for Python/Node.js function execution

---

## Project Structure

```
multicloudstack/
├── ministack/                            # Main source package
│   ├── app.py                            # ASGI application + dashboard route (~1240 lines)
│   ├── __main__.py                       # CLI entry point (`python -m ministack`)
│   ├── core/                             # Core infrastructure
│   │   ├── router.py                     # Multi-cloud router (provider + service detection)
│   │   ├── responses.py                  # AWS response formatting, AccountScopedDict
│   │   ├── responses_cloud.py            # Azure/Huawei/GCP response helpers
│   │   ├── persistence.py                # State persistence across restarts
│   │   ├── lambda_runtime.py             # Lambda/FunctionGraph warm worker pool
│   │   ├── auth_azure.py                 # Azure Bearer token, Shared Key, JWT stub
│   │   ├── auth_huawei.py                # Huawei AK/SK HMAC-SHA256, IAM token
│   │   ├── auth_gcp.py                   # GCP service account JWT, OAuth2, metadata server
│   │   └── azure_resource_id.py          # ARM Resource ID parser
│   ├── static/
│   │   └── dashboard.html                # Interactive multi-cloud dashboard
│   └── services/                         # Service emulators (102 total)
│       ├── s3.py, sqs.py, dynamodb.py    # 41+ AWS services (root-level files)
│       ├── iam_sts.py, lambda_svc.py     # ...
│       ├── cloudformation/               # CloudFormation engine (66+ provisioners)
│       ├── azure/                        # 29 Azure services
│       ├── huawei/                       # 17 Huawei Cloud services
│       │   ├── obs.py, iam_hw.py, smn.py, functiongraph.py
│       │   ├── huawei_extended.py        # Extended service stubs (DMS, AOM, CCE, etc.)
│       │   └── ... (individual modules importing from .huawei_extended)
│       └── gcp/                          # 14 GCP services
├── examples/
│   └── terraform/                        # Huawei Cloud OBS Terraform examples
│       ├── README.md                     # Documentation for all examples
│       ├── run_obs_examples.sh           # Interactive demo script
│       ├── obs-simple/                   # Minimal bucket + object example
│       ├── obs-bucket/                   # Comprehensive 8-bucket example
│       └── modules/obs-bucket/           # Reusable OBS bucket module
├── tests/                                # Test suite
│   ├── conftest.py                       # pytest fixtures
│   ├── test_*.py                         # AWS service tests
│   ├── test_azure_services.py            # Azure integration tests
│   ├── test_huawei_services.py           # Huawei integration tests
│   └── test_multicloud/                  # Multi-cloud functional tests
│       ├── test_storage.py, test_messaging.py, test_databases.py, ...
├── doc/                                  # Project documentation
├── docs/
│   └── DASHBOARD.md                      # Dashboard documentation
├── docker/                               # Docker init scripts (AWS, Azure, GCP, Huawei)
├── Testcontainers/                       # Python/Go/Java testcontainer examples
├── bin/                                  # CLI wrappers (awslocal, etc.)
├── Dockerfile                            # Multi-stage Docker build (Alpine-based)
├── docker-compose.yml                    # All-clouds mode
├── docker-compose.azure.yml              # Azure-only mode
├── docker-compose.huawei.yml             # Huawei-only mode
├── docker-compose.gcp.yml                # GCP-only mode
├── pyproject.toml                        # Python project config (build, deps, tools)
├── pytest.ini                            # Pytest configuration
├── Makefile                              # Build, run, test targets
├── requirements.txt / requirements-test.txt
└── README.md, README_AZURE.md, README_HUAWEI.md, README_GCP.md, README_TESTS.md
```

---

## Building and Running

### Prerequisites
- Python 3.10+
- Docker (optional, for containerized usage and real infrastructure)

### Quick Start

```bash
# Option 1: Run directly from source
pip install -e .
ministack

# Option 2: Uvicorn directly
python -m uvicorn ministack.app:app --host 0.0.0.0 --port 4566

# Option 3: Docker (all clouds)
docker compose up -d --build

# Option 4: Azure-only mode
docker compose -f docker-compose.azure.yml up -d

# Option 5: Huawei-only mode
docker compose -f docker-compose.huawei.yml up -d

# Option 6: GCP-only mode
docker compose -f docker-compose.gcp.yml up -d

# Verify
curl http://localhost:4566/_ministack/health    # AWS
curl http://localhost:4566/_azure/health         # Azure
curl http://localhost:4566/_huawei/health        # Huawei
curl http://localhost:4566/_gcp/health           # GCP
curl http://localhost:4566/_multicloud/health    # Consolidated

# Dashboard
open http://localhost:4566/dashboard
```

### Multi-Cloud Mode

Set `CLOUD_MODE` environment variable:

| Value | Behavior |
|-------|----------|
| `all` (default) | AWS + Azure + Huawei + GCP — provider auto-detected per request |
| `aws` | AWS services only (original MiniStack behavior) |
| `azure` | Azure services only |
| `huawei` | Huawei Cloud services only |
| `gcp` | GCP services only |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GATEWAY_PORT` | `4566` | Port to listen on |
| `CLOUD_MODE` | `all` | `aws` / `azure` / `huawei` / `gcp` / `all` |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `S3_PERSIST` | `0` | Enable disk persistence for S3 |
| `REDIS_HOST` | `redis` | Redis host for ElastiCache/DCS |
| `RDS_BASE_PORT` | `15432` | Base port for RDS/Azure SQL containers |
| `ELASTICACHE_BASE_PORT` | `16379` | Base port for Redis containers |
| `LAMBDA_EXECUTOR` | `local` | Lambda mode: `local` or `docker` |
| `PERSIST_STATE` | `0` | Persist service state across restarts |
| `AZURE_TENANT_ID` | `0000...0000` | Azure Tenant ID |
| `AZURE_SUBSCRIPTION_ID` | `0000...0001` | Azure Subscription ID |
| `HUAWEICLOUD_SDK_AK` | `test` | Huawei Access Key |
| `HUAWEICLOUD_PROJECT_ID` | `0000000000000000` | Huawei Project ID |
| `GCP_PROJECT_ID` | `ministack-emulator` | GCP Project ID |
| `GCP_REGION` | `us-central1` | GCP Region |
| `GCP_ZONE` | `us-central1-a` | GCP Zone |

### Makefile Targets

| Target | Command | Description |
|--------|---------|-------------|
| `build` | `make build` | Build Docker image |
| `run` | `make run` | Build and run container |
| `run-compose` | `make run-compose` | Run via Docker Compose |
| `test` | `make test` | Full integration test (builds, starts, exercises S3/SQS/DynamoDB/SNS/STS/Secrets/Lambda/ALB) |
| `health` | `make health` | Check health endpoint |
| `logs` | `make logs` | Follow container logs |
| `stop` | `make stop` | Stop and remove container |
| `clean` | `make clean` | Stop container and remove image |
| `purge` | `make purge` | Remove all orphaned containers/volumes/S3 data |
| `run-azure` | `make run-azure` | Start Azure-only mode |
| `run-huawei` | `make run-huawei` | Start Huawei-only mode |
| `run-gcp` | `make run-gcp` | Start GCP-only mode |

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# AWS tests
pytest tests/test_*.py -v -k "not azure and not huawei"

# Azure tests
pytest tests/test_azure_services.py -v

# Huawei tests
pytest tests/test_huawei_services.py -v

# GCP tests
pytest tests/test_gcp_services.py -v

# Multi-cloud tests
pytest tests/test_multicloud/ -v

# All tests (parallel)
pytest -n auto

# With coverage
pytest --cov=ministack --cov-report=html
```

---

## Development Conventions

### Code Style
- **Linter:** ruff with `E`, `F`, `I` rules; line length 120; target Python 3.10+
- Some intentional lint suppressions for emulator-specific patterns (E501, E402, F401, F811, F841, E741, F601)
- See `[tool.ruff.lint]` in `pyproject.toml` for full ignore list

### Service Module Pattern
Each service follows the same structure:
```python
# Module-level state using AccountScopedDict
_resources = AccountScopedDict()

# Persistence
def get_state(): ...
def restore_state(data): ...

# Main handler
async def handle_request(method, path, headers, body, query_params) -> tuple:
    return status, resp_headers, resp_body

# Reset (for testing)
def reset(): ...
```

### Huawei Extended Pattern
Huawei Cloud services in the `huawei/` subdirectory that wrap `huawei_extended.py` **must use relative imports**:
```python
# CORRECT — relative import (sibling module)
from .huawei_extended import handle_dms_request as handle_request, reset_dms as reset

# WRONG — absolute import (module not at package root)
# from ministack.services.huawei_extended import ...
```

### Adding a New Service

**AWS:**
1. Create `ministack/services/myservice.py` with `handle_request()` and `reset()`
2. Register in `SERVICE_HANDLERS` dict in `app.py`
3. Add detection patterns in `ministack/core/router.py`
4. Add test file in `tests/test_myservice.py`

**Azure:**
1. Create `ministack/services/azure/myservice.py` with same pattern
2. Register in `app.py` Azure handlers section
3. Add path prefix to `AZURE_SERVICE_PATTERNS` in `router.py`

**Huawei:**
1. Create `ministack/services/huawei/myservice.py` with same pattern
2. Register in `app.py` Huawei handlers section
3. Add path prefix to `HUAWEI_SERVICE_PATTERNS` in `router.py`

### Testing
- One test file per service (`test_*.py`)
- Integration tests via `boto3`/`azure-sdk`/`huaweicloudsdk`/`google-cloud-*` against local endpoint
- Parallel execution via `pytest-xdist`
- Serial tests marked with `@pytest.mark.serial` for global-state operations
- Multi-cloud functional tests in `tests/test_multicloud/`

### Dashboard Development
- Edit `ministack/static/dashboard.html`
- Rebuild Docker: `docker compose up -d --build`
- Refresh browser: `http://localhost:4566/dashboard`
- No hot reload — changes require container rebuild

---

## Internal API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/_ministack/health` | GET | AWS service health |
| `/_ministack/reset` | POST | Reset all AWS state |
| `/_ministack/config` | POST | Runtime config changes |
| `/_ministack/dashboard` | GET | Interactive multi-cloud dashboard |
| `/_azure/health` | GET | Azure service health |
| `/_azure/reset` | POST | Reset all Azure state |
| `/_huawei/health` | GET | Huawei service health |
| `/_huawei/reset` | POST | Reset all Huawei state |
| `/_gcp/health` | GET | GCP service health |
| `/_gcp/reset` | POST | Reset all GCP state |
| `/_multicloud/health` | GET | Consolidated all 4 clouds |
| `/_localstack/health` | GET | LocalStack-compatible health |
| `/` or `/dashboard` | GET | Dashboard HTML (redirects to dashboard.html) |

---

## Dependencies

### Core (no extras)
`uvicorn[standard]`, `httptools`, `pyyaml`, `defusedxml`

### Optional (`[full]`)
`duckdb` (Athena SQL), `docker` (real containers), `cryptography` (KMS/ACM), `psycopg2-binary` (PostgreSQL), `pymysql` (MySQL)

### Azure SDK (`[azure]`) — for client testing only
`azure-storage-blob`, `azure-identity`, `azure-cosmos`, `azure-keyvault-secrets`, `azure-servicebus`, `azure-monitor-query`

### Huawei SDK (`[huawei]`) — for client testing only
`huaweicloudsdkcore`, `huaweicloudsdkobs`, `huaweicloudsdkdms`, `huaweicloudsdksmn`, `huaweicloudsdkfunctiongraph`, `huaweicloudsdkrds`

### GCP SDK (`[gcp]`) — for client testing only
`google-cloud-storage`, `google-cloud-pubsub`, `google-cloud-functions`, `google-cloud-bigquery`, `google-cloud-secret-manager`, `google-cloud-kms`

### Dev (`[dev]`)
`boto3`, `pytest`, `pytest-xdist`, `pytest-cov`, `ruff`, plus all `[full]` deps

---

## Git Workflow

- **Main branch:** `main`
- **Feature branches:** `feat/<description>` or `fix/<description>`
- **Pull requests:** Create PR with comprehensive description
- **Commit style:** Conventional commits (`fix:`, `feat:`, `refactor:`, `docs:`, `test:`)
- **SSH remote:** `git@github.com:marcuscabrera/multicloudstack.git`

---

## License

MIT — free to use, modify, and distribute.
