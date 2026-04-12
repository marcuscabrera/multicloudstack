# MiniStack for Microsoft Azure

Local emulator for **Microsoft Azure** services, built on the MiniStack architecture.
Emulates 30 Azure services on a single port (`4566`), compatible with the official
`azure-sdk-for-python`, Terraform `azurerm` provider, and Azure CLI.

## Quick Start

### Docker (Azure Mode Only)

```bash
docker compose -f docker-compose.azure.yml up -d --build
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AZURE_MODE` | `0` | `0` = AWS only, `1` = Azure only, `2` = Hybrid |
| `AZURE_TENANT_ID` | `00000000-0000-0000-0000-000000000000` | Tenant ID |
| `AZURE_SUBSCRIPTION_ID` | `00000000-0000-0000-0000-000000000001` | Subscription ID |
| `AZURE_LOCATION` | `eastus` | Default region |
| `AZURE_STORAGE_ACCOUNT` | `devstoreaccount1` | Default storage account |
| `AZURE_CLIENT_ID` | `test` | Service Principal client_id |
| `AZURE_CLIENT_SECRET` | `test` | Service Principal client_secret |

## Supported Services

### Priority Services (Full Implementation)

| Service | Azure SDK | API Path | Status |
|---------|-----------|----------|--------|
| **Blob Storage** | `azure-storage-blob` | `/azure/blob/{account}/{container}/{blob}` | ✅ CRUD, compatible with Azurite |
| **Entra ID / AAD** | `azure-identity` | `/tenant/{tid}/oauth2/v2.0/token` | ✅ OAuth2 token, OIDC discovery, JWKS |
| **Service Bus** | `azure-servicebus` | `/subscriptions/{sub}/.../queues` | ✅ Queues, Topics, Send/Receive |
| **Azure Functions** | `azure-functions` | `/api/{funcName}` | ✅ CRUD, HTTP trigger, warm workers |
| **Cosmos DB** | `azure-cosmos` | `/azure/cosmos/{account}/dbs/{db}/colls/{coll}/docs` | ✅ NoSQL API, SQL queries |
| **Key Vault Secrets** | `azure-keyvault-secrets` | `/keyvault/{vault}/secrets/{name}` | ✅ CRUD, versions |
| **Azure SQL / PostgreSQL** | `azure-mgmt-rdbms` | `/subscriptions/{sub}/.../servers` | ✅ Server + Database CRUD |
| **Cache for Redis** | `azure-mgmt-redis` | `/subscriptions/{sub}/.../redis` | ✅ Instance CRUD |
| **Monitor Logs** | `azure-monitor-query` | `/workspaces/{id}/query` | ✅ Ingest, KQL-like queries |
| **ARM Deployments** | `azure-mgmt-resource` | `/subscriptions/{sub}/.../deployments` | ✅ ARM JSON templates |

### Extended Services

| Service | API Path | Description |
|---------|----------|-------------|
| Key Vault Keys | `/keyvault/{vault}/keys` | Key CRUD, encrypt/decrypt stubs |
| Key Vault Certificates | `/keyvault/{vault}/certificates` | Certificate CRUD |
| Monitor Metrics | `/subscriptions/{sub}/.../metrics` | Metric publish/query |
| Event Hubs | `/subscriptions/{sub}/.../eventhubs` | Hub CRUD, send/receive |
| Event Grid | `/subscriptions/{sub}/.../topics` | Topic CRUD, publish events |
| Virtual Machines | `/subscriptions/{sub}/.../virtualMachines` | VM CRUD, actions |
| Container Instances | `/subscriptions/{sub}/.../containerGroups` | ACI CRUD |
| Container Registry | `/subscriptions/{sub}/.../registries` | ACR CRUD |
| CDN / Front Door | `/subscriptions/{sub}/.../profiles` | CDN profiles |
| Logic Apps | `/subscriptions/{sub}/.../workflows` | Workflow CRUD |
| AAD B2C | `/tenant/{tid}/oauth2` | B2C authentication |
| Data Factory | `/subscriptions/{sub}/.../factories` | Factory CRUD |
| Synapse Analytics | `/subscriptions/{sub}/.../workspaces` | Workspace CRUD, SQL |
| Communication Email | `/subscriptions/{sub}/.../emails` | Email sending |
| DNS | `/subscriptions/{sub}/.../dnsZones` | DNS zone CRUD |
| Load Balancer | `/subscriptions/{sub}/.../loadBalancers` | LB CRUD |
| App Configuration | `/kv/{key}` | Key-value store |
| Stream Analytics | `/subscriptions/{sub}/.../streamingjobs` | Job CRUD, start/stop |
| Storage Queue | `/azure/queue/{name}/messages` | Queue CRUD, send/receive |
| API Management | `/subscriptions/{sub}/.../service` | APIM CRUD |

## Admin Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/_azure/health` | GET | Azure service health check |
| `/_azure/reset` | POST | Reset all Azure service state |

## Usage Examples

### Python SDK

```python
from azure.identity import ClientSecretCredential
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient
from azure.keyvault.secrets import SecretClient

BASE = "http://localhost:4566"

# Entra ID credential
cred = ClientSecretCredential(
    tenant_id="00000000-0000-0000-0000-000000000000",
    client_id="test",
    client_secret="test",
    authority=BASE,
)

# Blob Storage
blob_client = BlobServiceClient(
    account_url=f"{BASE}/azure/blob/devstoreaccount1",
    credential="test"
)
container = blob_client.create_container("mycontainer")
container.upload_blob("hello.txt", b"Hello Azure!")

# Cosmos DB
cosmos_client = CosmosClient(
    url=f"{BASE}/azure/cosmos/devaccount",
    credential="test"
)
db = cosmos_client.create_database("mydb")
container = db.create_container("mycontainer", partition_key="/id")
container.create_item({"id": "1", "name": "Alice"})

# Key Vault Secrets
secret_client = SecretClient(
    vault_url=f"{BASE}/keyvault/myVault",
    credential=cred
)
secret_client.set_secret("db-password", "s3cr3t")
secret = secret_client.get_secret("db-password")
print(secret.value)  # s3cr3t
```

### Raw HTTP

```python
import requests, json

BASE = "http://localhost:4566"

# 1. Get Entra ID token
resp = requests.post(
    f"{BASE}/tenant/00000000-0000-0000-0000-000000000000/oauth2/v2.0/token",
    data="grant_type=client_credentials&client_id=test&client_secret=test&scope=https://management.azure.com/.default",
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)
token = resp.json()["access_token"]

# 2. Create Blob container
requests.put(
    f"{BASE}/azure/blob/devstoreaccount1/mycontainer?restype=container",
    headers={"Authorization": f"Bearer {token}"}
)

# 3. Upload blob
requests.put(
    f"{BASE}/azure/blob/devstoreaccount1/mycontainer/hello.txt",
    data=b"Hello Azure!",
    headers={"Authorization": f"Bearer {token}"}
)

# 4. Create Azure Function
requests.post(
    f"{BASE}/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/dev-rg/providers/Microsoft.Web/sites/myapp/functions/hello",
    json={"name": "hello"},
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
)

# 5. Invoke function
resp = requests.post(f"{BASE}/api/hello", json={"name": "Azure"})
print(resp.json())
```

### Terraform azurerm

```hcl
provider "azurerm" {
  features {}
  skip_provider_registration = true

  tenant_id       = "00000000-0000-0000-0000-000000000000"
  subscription_id = "00000000-0000-0000-0000-000000000001"
  client_id       = "test"
  client_secret   = "test"

  # Note: Terraform azurerm requires custom endpoint support;
  # use with local backend or mock provider for full compatibility.
}

resource "azurerm_resource_group" "dev" {
  name     = "dev-rg"
  location = "East US"
}
```

## Operation Modes

| `AZURE_MODE` | Behavior |
|---|---|
| `0` (default) | AWS services only (original MiniStack) |
| `1` | Azure Cloud services only |
| `2` | Hybrid — both AWS and Azure active (Azure headers/paths take precedence) |

## Running Tests

```bash
# Set Azure mode
export AZURE_MODE=1

# Start the server
python -m uvicorn ministack.app:app --host 0.0.0.0 --port 4566 &

# Run Azure tests
pytest tests/test_azure_services.py -v
```

## Architecture

```
Request → Router (detect_service)
  ├── AZURE_MODE=1: Azure path/header detection → Azure services
  ├── AZURE_MODE=2: Azure headers/paths take precedence over AWS
  └── AZURE_MODE=0: AWS services only (original)

Azure Service Mapping:
  Blob Storage     → In-memory containers/blobs (Azurite-compatible)
  Entra ID         → JWT stub tokens, OIDC discovery
  Functions        → lambda_runtime.py warm worker pool
  Cosmos DB        → In-memory documents, SQL query stub
  Key Vault        → In-memory secrets/keys/certs
  Azure SQL        → Server metadata (real containers optional)
  Cache Redis      → Instance metadata (real Redis optional)
  Monitor          → In-memory log ingestion + query
  ARM Deployments  → ARM JSON template processing
  Extended services → Lightweight stubs
```

## Differences from Real Azure

- All services are **in-memory** emulators (no persistent infrastructure by default)
- Azure SQL/Redis return **emulated endpoints** (not real containers unless Docker integration is added)
- Authentication uses **simplified credentials** (default: `test`/`test`)
- JWT tokens are **structurally valid but not cryptographically signed**
- No **billing, quotas, rate limiting, or RBAC**
- No **real networking** (all endpoints are localhost)
- ARM deployments process templates but don't create real Azure resources

## License

MIT — same as MiniStack upstream.
