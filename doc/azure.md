# Azure Services

## Overview

MiniStack emulates **30 Azure services** on port `4566`. Services are detected via `x-ms-*` headers, Bearer/SharedKey auth, or `/subscriptions/`, `/tenant/`, `/azure/` path prefixes.

## Quick Start

```bash
./bin/ministack-start azure

# Verify
curl http://localhost:4566/_azure/health
```

## Identity (Entra ID / AAD)

### Obtain OAuth2 Token

```bash
curl -X POST "http://localhost:4566/tenant/00000000-0000-0000-0000-000000000000/oauth2/v2.0/token" \
  -d "grant_type=client_credentials&client_id=test&client_secret=test&scope=https://management.azure.com/.default" \
  -H "Content-Type: application/x-www-form-urlencoded"
```

Response:
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### OIDC Discovery

```bash
curl http://localhost:4566/tenant/00000000-0000-0000-0000-000000000000/.well-known/openid-configuration
```

**Python:**

```python
from azure.identity import ClientSecretCredential

cred = ClientSecretCredential(
    tenant_id="00000000-0000-0000-0000-000000000000",
    client_id="test",
    client_secret="test",
    authority="http://localhost:4566",
)
token = cred.get_token("https://management.azure.com/.default")
print(token.token[:20] + "...")
```

## Blob Storage

### Create Container

```bash
curl -X PUT "http://localhost:4566/azure/blob/devstoreaccount1/mycontainer?restype=container" \
  -H "Authorization: Bearer test-token"
```

### Upload Blob

```bash
curl -X PUT "http://localhost:4566/azure/blob/devstoreaccount1/mycontainer/hello.txt" \
  -d "Hello Azure!" \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: text/plain"
```

### Download Blob

```bash
curl "http://localhost:4566/azure/blob/devstoreaccount1/mycontainer/hello.txt" \
  -H "Authorization: Bearer test-token"
```

### List Containers

```bash
curl "http://localhost:4566/azure/blob/devstoreaccount1" \
  -H "Authorization: Bearer test-token"
```

**Python:**

```python
from azure.storage.blob import BlobServiceClient

client = BlobServiceClient(
    account_url="http://localhost:4566/azure/blob/devstoreaccount1",
    credential="test"
)
container = client.create_container("my-container")
container.upload_blob("hello.txt", b"Hello Azure!")
blob = container.download_blob("hello.txt")
print(blob.readall())
```

## Service Bus

### Create Queue

```bash
curl -X PUT "http://localhost:4566/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/dev-rg/providers/Microsoft.ServiceBus/namespaces/devns/queues/my-queue" \
  -H "Authorization: Bearer test-token"
```

### Publish Message

```bash
curl -X POST "http://localhost:4566/azure/servicebus/devns/my-queue/messages" \
  -d '{"body": "Hello Service Bus"}' \
  -H "Authorization: Bearer test-token"
```

### Receive Message

```bash
curl -X DELETE "http://localhost:4566/azure/servicebus/devns/my-queue/messages/head" \
  -H "Authorization: Bearer test-token"
```

## Azure Functions

### Create Function

```bash
curl -X POST "http://localhost:4566/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/dev-rg/providers/Microsoft.Web/sites/myapp/functions/hello" \
  -d '{"name": "hello", "code": {"zip": ""}}' \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json"
```

### Invoke Function

```bash
curl -X POST "http://localhost:4566/api/hello" \
  -d '{"name": "Azure"}' \
  -H "Content-Type: application/json"
```

## Cosmos DB

### Create Database

```bash
curl -X POST "http://localhost:4566/azure/cosmos/devaccount/dbs" \
  -d '{"id": "mydb"}' \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json"
```

### Create Container

```bash
curl -X POST "http://localhost:4566/azure/cosmos/devaccount/dbs/mydb/colls" \
  -d '{"id": "users", "partitionKey": {"paths": ["/id"]}}' \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json"
```

### Insert Document

```bash
curl -X POST "http://localhost:4566/azure/cosmos/devaccount/dbs/mydb/colls/users/docs" \
  -d '{"id": "1", "name": "Alice"}' \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json"
```

## Key Vault

### Create Secret

```bash
curl -X PUT "http://localhost:4566/keyvault/myVault/secrets/db-password" \
  -d '{"value": "s3cr3t"}' \
  -H "Authorization: Bearer test-token"
```

### Get Secret

```bash
curl "http://localhost:4566/keyvault/myVault/secrets/db-password" \
  -H "Authorization: Bearer test-token"
```

## Azure SQL / PostgreSQL

```bash
curl -X PUT "http://localhost:4566/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/dev-rg/providers/Microsoft.Sql/servers/my-sql" \
  -d '{"properties": {"administratorLogin": "azure", "version": "14"}}' \
  -H "Authorization: Bearer test-token"
```

## ARM Deployments

```bash
curl -X PUT "http://localhost:4566/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/dev-rg/providers/Microsoft.Resources/deployments/my-deploy" \
  -d '{
    "properties": {
      "mode": "Incremental",
      "template": {"$schema": "https://schema.management.azure.com/...", "resources": []}
    }
  }' \
  -H "Authorization: Bearer test-token"
```

## Complete Service List

| Service | API Path | Status |
|---------|----------|--------|
| Blob Storage | `/azure/blob/{account}/{container}/{blob}` | ✅ |
| Entra ID | `/tenant/{tid}/oauth2/v2.0/token` | ✅ |
| Service Bus | `/subscriptions/{sub}/.../queues` | ✅ |
| Functions | `/api/{funcName}` | ✅ |
| Cosmos DB | `/azure/cosmos/{account}/dbs/{db}/colls` | ✅ |
| Key Vault Secrets | `/keyvault/{vault}/secrets/{name}` | ✅ |
| Key Vault Keys | `/keyvault/{vault}/keys/{name}` | ✅ |
| Key Vault Certs | `/keyvault/{vault}/certificates/{name}` | ✅ |
| Azure SQL | `/subscriptions/{sub}/.../servers` | ✅ |
| Cache Redis | `/subscriptions/{sub}/.../redis` | ✅ |
| Monitor Logs | `/workspaces/{id}/query` | ✅ |
| Monitor Metrics | `/subscriptions/{sub}/.../metrics` | ✅ |
| Event Hubs | `/subscriptions/{sub}/.../eventhubs` | ✅ |
| Event Grid | `/subscriptions/{sub}/.../topics` | ✅ |
| Virtual Machines | `/subscriptions/{sub}/.../virtualMachines` | ✅ |
| Container Instances | `/subscriptions/{sub}/.../containerGroups` | ✅ |
| Container Registry | `/subscriptions/{sub}/.../registries` | ✅ |
| ARM Deployments | `/subscriptions/{sub}/.../deployments` | ✅ |
| CDN / Front Door | `/subscriptions/{sub}/.../profiles` | ✅ |
| Logic Apps | `/subscriptions/{sub}/.../workflows` | ✅ |
| AAD B2C | `/tenant/{tid}/oauth2` | ✅ |
| Data Factory | `/subscriptions/{sub}/.../factories` | ✅ |
| Synapse | `/subscriptions/{sub}/.../workspaces` | ✅ |
| Communication Email | `/subscriptions/{sub}/.../emails` | ✅ |
| DNS | `/subscriptions/{sub}/.../dnsZones` | ✅ |
| Load Balancer | `/subscriptions/{sub}/.../loadBalancers` | ✅ |
| App Configuration | `/kv/{key}` | ✅ |
| Stream Analytics | `/subscriptions/{sub}/.../streamingjobs` | ✅ |
| Storage Queue | `/azure/queue/{name}/messages` | ✅ |
| API Management | `/subscriptions/{sub}/.../service` | ✅ |

## Admin Endpoints

```bash
curl http://localhost:4566/_azure/health
curl -X POST http://localhost:4566/_azure/reset
```
