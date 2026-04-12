# PROMPT: Adaptar MiniStack para emular serviços Microsoft Azure

## Contexto do Projeto Base

O MiniStack (<https://github.com/ministackorg/ministack>) é um emulador local
de AWS em Python/ASGI, com 41 serviços isolados em `ministack/services/`,
cada um implementando `async def handle_request(scope, receive, send)` e
uma função `reset()`. O roteador em `ministack/core/router.py` dispatcha
requisições por header (`X-Amz-Target`), path prefix e query params.
O dispatcher central é `ministack/app.py`.

## Objetivo

Criar "AzureStack" — uma variante do MiniStack que emule localmente os
principais serviços da Microsoft Azure, mantendo a mesma arquitetura
modular, leveza (~300MB Docker, <50MB RAM idle, <2s startup) e
compatibilidade transparente com os SDKs oficiais `azure-sdk-for-python`
e ferramentas como Terraform `azurerm`, Azure CLI e Bicep.

O projeto deve ser um fork do MiniStack com modo dual:

- `AZURE_MODE=0` → comportamento AWS original inalterado
- `AZURE_MODE=1` → emulação Azure, porta 4566 (ou `AZURE_PORT`)
- `AZURE_MODE=2` → modo híbrido, ambos ativos em prefixos de path distintos

---

## Mapeamento de Serviços AWS → Azure

| Serviço MiniStack (AWS) | Equivalente Azure        | SDK Python (`azure-*`)              | Prefixo REST Azure               |
|-------------------------|--------------------------|-------------------------------------|----------------------------------|
| `s3.py`                 | Azure Blob Storage       | `azure-storage-blob`                | `/v3/{account}/containers`       |
| `sqs.py`                | Azure Service Bus        | `azure-servicebus`                  | `/subscriptions/{sub}/...queues` |
| `sns.py`                | Azure Event Grid         | `azure-eventgrid`                   | `/subscriptions/{sub}/...topics` |
| `dynamodb.py`           | Azure Cosmos DB (NoSQL)  | `azure-cosmos`                      | `/dbs/{db}/colls/{coll}/docs`    |
| `lambda_svc.py`         | Azure Functions          | `azure-functions`                   | `/api/{funcName}`                |
| `rds.py`                | Azure SQL / PostgreSQL   | `azure-mgmt-rdbms`                  | `/subscriptions/{sub}/...servers`|
| `elasticache.py`        | Azure Cache for Redis    | `azure-mgmt-redis`                  | `/subscriptions/{sub}/...redis`  |
| `cloudwatch_logs.py`    | Azure Monitor / Log Analytics | `azure-monitor-query`          | `/api/logs/v1/workspaces/{id}`   |
| `cloudwatch.py`         | Azure Monitor Metrics    | `azure-monitor-metrics-advisor`     | `/subscriptions/{sub}/providers/microsoft.insights/metrics` |
| `secretsmanager.py`     | Azure Key Vault Secrets  | `azure-keyvault-secrets`            | `/{vault}.vault.azure.net/secrets` |
| `kms.py`                | Azure Key Vault Keys     | `azure-keyvault-keys`               | `/{vault}.vault.azure.net/keys`  |
| `iam_sts.py`            | Azure Active Directory / Entra ID | `azure-identity`           | `/tenant/{tid}/oauth2/v2.0/token`|
| `kinesis.py`            | Azure Event Hubs         | `azure-eventhub`                    | `/subscriptions/{sub}/...eventhubs` |
| `ec2.py`                | Azure Virtual Machines   | `azure-mgmt-compute`                | `/subscriptions/{sub}/...virtualMachines` |
| `ecs.py`                | Azure Container Instances (ACI) / AKS | `azure-mgmt-containerinstance` | `/subscriptions/{sub}/...containerGroups` |
| `ecr.py`                | Azure Container Registry (ACR) | `azure-mgmt-containerregistry` | `/subscriptions/{sub}/...registries` |
| `apigateway.py`         | Azure API Management     | `azure-mgmt-apimanagement`          | `/subscriptions/{sub}/...service/{name}` |
| `cloudformation`        | Azure Resource Manager (ARM) / Bicep | `azure-mgmt-resource`   | `/subscriptions/{sub}/deployments` |
| `cloudfront.py`         | Azure CDN / Front Door   | `azure-mgmt-cdn`                    | `/subscriptions/{sub}/...profiles` |
| `stepfunctions.py`      | Azure Logic Apps / Durable Functions | `azure-mgmt-logic`       | `/subscriptions/{sub}/...workflows` |
| `cognito.py`            | Azure Active Directory B2C | `azure-identity` + MSAL            | `/tenant/{tid}/oauth2/v2.0`      |
| `glue.py`               | Azure Data Factory       | `azure-mgmt-datafactory`            | `/subscriptions/{sub}/...factories` |
| `athena.py`             | Azure Synapse Analytics  | `azure-synapse-spark`               | `/workspaces/{ws}/sql/...`       |
| `ses.py`                | Azure Communication Services (Email) | `azure-communication-email` | `/emails:send?api-version=2023-03-31` |
| `route53.py`            | Azure DNS                | `azure-mgmt-dns`                    | `/subscriptions/{sub}/...dnsZones` |
| `alb.py`                | Azure Load Balancer / App Gateway | `azure-mgmt-network`      | `/subscriptions/{sub}/...loadBalancers` |
| `acm.py`                | Azure Key Vault Certificates | `azure-keyvault-certificates`   | `/{vault}.vault.azure.net/certificates` |
| `waf.py`                | Azure WAF / Front Door WAF | `azure-mgmt-frontdoor`            | `/subscriptions/{sub}/...webApplicationFirewallPolicies` |
| `ssm.py`                | Azure App Configuration  | `azure-appconfiguration`            | `/{account}.azconfig.io/kv`      |
| `firehose.py`           | Azure Stream Analytics   | `azure-mgmt-streamanalytics`        | `/subscriptions/{sub}/...streamingjobs` |
| `codebuild.py`          | Azure DevOps Pipelines   | `azure-devops`                      | `/{org}/_apis/pipelines`         |
| `emr.py`                | Azure HDInsight          | `azure-mgmt-hdinsight`              | `/subscriptions/{sub}/...clusters` |

---

## Requisitos de Autenticação Azure

### 1. Azure Identity (Bearer Token)

Todas as chamadas de Management API usam OAuth 2.0 Bearer Token:

```
Authorization: Bearer {access_token}
```

O emulador deve implementar um endpoint IAM local que emite tokens JWT stub:

```
POST /tenant/{tenantId}/oauth2/v2.0/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_id=test
&client_secret=test
&scope=https://management.azure.com/.default
```

Resposta esperada:

```json
{
  "access_token": "<JWT stub válido>",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### 2. Azure Storage Shared Key

Para Blob Storage, File Storage e Queue Storage, suportar autenticação
via header `Authorization: SharedKey {account}:{signature}` e também
aceitar qualquer valor (modo permissivo de dev).

### 3. Azure Key Vault

Key Vault usa seu próprio endpoint:

```
https://{vaultName}.vault.azure.net
```

No emulador, mapear para:

```
http://localhost:4566/keyvault/{vaultName}
```

### 4. Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `AZURE_MODE` | `0` | `1` ativa modo Azure, `2` modo híbrido |
| `AZURE_TENANT_ID` | `00000000-0000-0000-0000-000000000000` | Tenant ID padrão |
| `AZURE_SUBSCRIPTION_ID` | `00000000-0000-0000-0000-000000000001` | Subscription ID padrão |
| `AZURE_RESOURCE_GROUP` | `dev-rg` | Resource Group padrão |
| `AZURE_LOCATION` | `eastus` | Região padrão |
| `AZURE_CLIENT_ID` | `test` | Service Principal client_id |
| `AZURE_CLIENT_SECRET` | `test` | Service Principal secret |
| `AZURE_PORT` | `4566` | Porta do gateway (compartilhada) |
| `AZURE_STORAGE_ACCOUNT` | `devstoreaccount1` | Conta de storage padrão |

---

## Estrutura de URL Azure vs. Emulador

As URLs Azure Management seguem o padrão:

```
https://management.azure.com/subscriptions/{subId}/resourceGroups/{rg}/
    providers/{provider}/{resourceType}/{name}?api-version={ver}
```

No emulador, mapear para:

```
http://localhost:4566/azure/management/subscriptions/{subId}/
    resourceGroups/{rg}/providers/{provider}/{resourceType}/{name}
```

Para serviços com endpoint próprio (Blob, Key Vault, Event Hubs):

```
# Azure real:
https://{account}.blob.core.windows.net/{container}/{blob}

# Emulador (compatível com Azurite):
http://localhost:4566/azure/blob/{account}/{container}/{blob}
# OU modo compatível Azurite direto:
http://localhost:10000/{account}/{container}/{blob}
```

> **Nota de Compatibilidade com Azurite**: Para Blob Storage, Queue Storage
> e Table Storage, o emulador DEVE ser compatível com o protocolo Azurite
> (Microsoft's official Azure Storage emulator), expondo opcionalmente nas
> portas 10000 (Blob), 10001 (Queue), 10002 (Table) para drop-in replacement.

---

## Estrutura de Arquivos a Criar

```
ministack/
├── services/
│   ├── azure/                          # Novo subdiretório para serviços Azure
│   │   ├── __init__.py
│   │   ├── blob_storage.py             # Azure Blob Storage (compatível Azurite)
│   │   ├── service_bus.py              # Azure Service Bus (filas e tópicos)
│   │   ├── event_grid.py               # Azure Event Grid
│   │   ├── cosmos_db.py                # Azure Cosmos DB (NoSQL API)
│   │   ├── functions.py                # Azure Functions (Python + Node.js)
│   │   ├── azure_sql.py                # Azure SQL / PostgreSQL Flexible Server
│   │   ├── cache_redis.py              # Azure Cache for Redis
│   │   ├── monitor_logs.py             # Azure Monitor Logs (Log Analytics)
│   │   ├── monitor_metrics.py          # Azure Monitor Metrics
│   │   ├── keyvault_secrets.py         # Key Vault — Secrets
│   │   ├── keyvault_keys.py            # Key Vault — Keys (criptografia)
│   │   ├── keyvault_certs.py           # Key Vault — Certificates
│   │   ├── entra_id.py                 # Azure Entra ID / AAD (OAuth2, OIDC)
│   │   ├── event_hubs.py               # Azure Event Hubs (streaming)
│   │   ├── virtual_machines.py         # Azure VMs (control plane)
│   │   ├── container_instances.py      # ACI — Azure Container Instances
│   │   ├── container_registry.py       # ACR — Azure Container Registry
│   │   ├── api_management.py           # Azure API Management
│   │   ├── arm_deployments.py          # ARM Templates / Bicep deployments
│   │   ├── cdn_frontdoor.py            # Azure CDN / Front Door
│   │   ├── logic_apps.py               # Azure Logic Apps
│   │   ├── aad_b2c.py                  # Azure AD B2C (autenticação)
│   │   ├── data_factory.py             # Azure Data Factory
│   │   ├── synapse.py                  # Azure Synapse Analytics (SQL)
│   │   ├── communication_email.py      # Azure Communication Services Email
│   │   ├── dns.py                      # Azure DNS
│   │   ├── load_balancer.py            # Azure Load Balancer / App Gateway
│   │   ├── app_configuration.py        # Azure App Configuration (KV store)
│   │   ├── stream_analytics.py         # Azure Stream Analytics
│   │   └── storage_queue.py            # Azure Storage Queue
├── core/
│   ├── router.py                       # Atualizar: detectar requisições Azure
│   ├── auth_azure.py                   # NOVO: validação Bearer Token e Shared Key
│   └── azure_resource_id.py            # NOVO: parser de ARM Resource IDs
└── app.py                              # Registrar handlers Azure

# Novos arquivos raiz:
docker-compose.azure.yml                # Compose para modo Azure isolado
README_AZURE.md                         # Documentação com exemplos SDK Python
tests/
└── test_azure_services.py              # Suite de testes dos 10 serviços prioritários
```

---

## Serviços Prioritários (Fase 1 — implementar primeiro)

### 1. Azure Blob Storage (`blob_storage.py`)

Reutilizar o handler `s3.py` existente como base — Blob Storage e S3 têm
semântica similar (container = bucket, blob = object). Implementar:

- `PUT /azure/blob/{account}/{container}` — criar container
- `PUT /azure/blob/{account}/{container}/{blob}` — upload blob
- `GET /azure/blob/{account}/{container}/{blob}` — download blob
- `GET /azure/blob/{account}/{container}?restype=container&comp=list` — listar blobs
- `DELETE /azure/blob/{account}/{container}/{blob}` — deletar blob
- Headers Azure obrigatórios: `x-ms-request-id`, `x-ms-version`, `x-ms-date`
- Compatibilidade com `azure-storage-blob` SDK:

```python
from azure.storage.blob import BlobServiceClient
client = BlobServiceClient(
    account_url="http://localhost:4566/azure/blob/devstoreaccount1",
    credential="test"
)
container = client.get_container_client("mycontainer")
container.create_container()
container.upload_blob("hello.txt", b"Hello AzureStack!")
```

### 2. Azure Entra ID / AAD (`entra_id.py`)

Emitir tokens OAuth2 stub para viabilizar todos os outros serviços:

- `POST /tenant/{tid}/oauth2/v2.0/token` — token endpoint
- `GET /tenant/{tid}/.well-known/openid-configuration` — OIDC discovery
- `GET /tenant/{tid}/discovery/v2.0/keys` — JWKS endpoint
- Compatibilidade com `azure-identity` SDK:

```python
from azure.identity import ClientSecretCredential
cred = ClientSecretCredential(
    tenant_id="00000000-0000-0000-0000-000000000000",
    client_id="test",
    client_secret="test",
    authority="http://localhost:4566"
)
token = cred.get_token("https://management.azure.com/.default")
```

### 3. Azure Service Bus (`service_bus.py`)

Reutilizar a lógica do `sqs.py` como base:

- `PUT /subscriptions/{sub}/resourceGroups/{rg}/providers/
   Microsoft.ServiceBus/namespaces/{ns}/queues/{queue}` — criar fila
- `POST /{ns}.servicebus.windows.net/{queue}/messages` — enviar mensagem
- `DELETE /{ns}.servicebus.windows.net/{queue}/messages/head` — receive+delete
- Compatibilidade com `azure-servicebus` SDK:

```python
from azure.servicebus import ServiceBusClient, ServiceBusMessage
client = ServiceBusClient(
    fully_qualified_namespace="devnamespace.servicebus.local",
    credential="test",
    transport_type=...,   # apontar para localhost:4566
)
```

### 4. Azure Functions (`functions.py`)

Reutilizar a lógica do `lambda_svc.py` como base:

- `POST /subscriptions/{sub}/resourceGroups/{rg}/providers/
   Microsoft.Web/sites/{name}/functions/{funcName}` — criar function
- `POST /api/{funcName}` — invocar function (HTTP trigger)
- Suporte a Python 3.11+ e Node.js 20 (reutilizar executor warm do Lambda)
- Variável de ambiente injetada: `AZURE_FUNCTIONS_ENVIRONMENT=Development`

### 5. Azure Cosmos DB (`cosmos_db.py`)

Emular a API NoSQL (Core SQL) do Cosmos DB:

- `POST /{account}.documents.azure.com/dbs` — criar database
- `POST /{account}.documents.azure.com/dbs/{db}/colls` — criar container
- `POST /{account}.documents.azure.com/dbs/{db}/colls/{coll}/docs` — inserir doc
- `GET  /{account}.documents.azure.com/dbs/{db}/colls/{coll}/docs/{id}` — obter doc
- `POST /{account}.documents.azure.com/dbs/{db}/colls/{coll}/docs`
  com header `x-ms-documentdb-isquery: true` — query SQL
- Compatibilidade com `azure-cosmos` SDK:

```python
from azure.cosmos import CosmosClient
client = CosmosClient(
    url="http://localhost:4566/azure/cosmos/devaccount",
    credential="test"
)
db = client.create_database("mydb")
container = db.create_container("mycontainer", partition_key="/id")
container.create_item({"id": "1", "name": "Alice"})
```

### 6. Azure Key Vault Secrets (`keyvault_secrets.py`)

Reutilizar a lógica do `secretsmanager.py` como base:

- `PUT /keyvault/{vault}/secrets/{name}` — criar/atualizar secret
- `GET /keyvault/{vault}/secrets/{name}/{version}` — obter secret
- `GET /keyvault/{vault}/secrets` — listar secrets
- `DELETE /keyvault/{vault}/secrets/{name}` — deletar (soft-delete)
- Compatibilidade com `azure-keyvault-secrets` SDK:

```python
from azure.keyvault.secrets import SecretClient
client = SecretClient(
    vault_url="http://localhost:4566/keyvault/myVault",
    credential=cred
)
client.set_secret("db-password", "s3cr3t")
secret = client.get_secret("db-password")
print(secret.value)  # s3cr3t
```

### 7. Azure SQL / PostgreSQL Flexible (`azure_sql.py`)

Reutilizar a lógica de `rds.py` — spin up container Docker real:

- `PUT .../servers/{name}` — criar servidor (spin up Postgres/MySQL real)
- `PUT .../servers/{name}/databases/{db}` — criar database
- Retornar `fullyQualifiedDomainName` com `localhost:{port}` real
- Compatibilidade com `psycopg2` e `pyodbc` direto no endpoint retornado

### 8. Azure Cache for Redis (`cache_redis.py`)

Reutilizar a lógica de `elasticache.py` — spin up Redis real via Docker:

- `PUT .../redis/{name}` — criar instância Redis (container real)
- Retornar `hostName: localhost`, `port: {port}` real
- Compatibilidade com `azure-mgmt-redis` + `redis-py`

### 9. Azure Monitor Logs / Log Analytics (`monitor_logs.py`)

Reutilizar a lógica de `cloudwatch_logs.py`:

- `POST /workspaces/{workspaceId}/query` — executar query KQL (Kusto)
- `POST /workspaces/{workspaceId}/tables/{table}/rows` — ingerir logs
- Suporte básico a KQL: `where`, `project`, `summarize`, `order by`
- Compatibilidade com `azure-monitor-query` SDK

### 10. Azure Resource Manager — ARM Deployments (`arm_deployments.py`)

Equivalente ao CloudFormation — orquestrar criação de recursos via template:

- `PUT .../deployments/{name}` — criar deployment
- `GET .../deployments/{name}` — status (`Running` → `Succeeded`)
- `GET .../deployments/{name}/operations` — listar operações
- Suporte a templates ARM (JSON) com `parameters`, `variables`, `resources`
- Compatibilidade com Terraform `azurerm` provider e Azure CLI `az deployment`

---

## Compatibilidade com Ferramentas

### Terraform azurerm Provider

```hcl
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
  skip_provider_registration = true
  
  # Redirecionar para emulador local
  environment     = "public"
  tenant_id       = "00000000-0000-0000-0000-000000000000"
  subscription_id = "00000000-0000-0000-0000-000000000001"
  client_id       = "test"
  client_secret   = "test"
  
  # Override de endpoints
  endpoint {
    resource_manager = "http://localhost:4566/azure/management"
    active_directory  = "http://localhost:4566/tenant"
  }
}

resource "azurerm_resource_group" "dev" {
  name     = "dev-rg"
  location = "East US"
}
```

### Azure CLI

```bash
export AZURE_TENANT_ID=00000000-0000-0000-0000-000000000000
export AZURE_SUBSCRIPTION_ID=00000000-0000-0000-0000-000000000001

az configure --defaults \
  cloud="AzureCloud" \
  resource_manager_url="http://localhost:4566/azure/management"

az login --service-principal \
  -u test -p test \
  --tenant 00000000-0000-0000-0000-000000000000

az storage container create --name mycontainer \
  --account-name devstoreaccount1 \
  --account-key "test" \
  --blob-endpoint "http://localhost:4566/azure/blob/devstoreaccount1"

az functionapp create --resource-group dev-rg \
  --name my-func --runtime python --runtime-version 3.11
```

### Python azure-sdk-for-python

```python
from azure.identity import ClientSecretCredential
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient
from azure.keyvault.secrets import SecretClient

# Credencial reutilizável
cred = ClientSecretCredential(
    tenant_id="00000000-0000-0000-0000-000000000000",
    client_id="test",
    client_secret="test",
    authority="http://localhost:4566",  # apontar para emulador
)

# Blob Storage
blob_client = BlobServiceClient(
    account_url="http://localhost:4566/azure/blob/devstoreaccount1",
    credential="test"
)

# Cosmos DB
cosmos_client = CosmosClient(
    url="http://localhost:4566/azure/cosmos/devaccount",
    credential="test"
)

# Key Vault Secrets
secret_client = SecretClient(
    vault_url="http://localhost:4566/keyvault/myVault",
    credential=cred
)
```

---

## Módulo de Autenticação (`ministack/core/auth_azure.py`)

```python
# Interface mínima esperada:

async def validate_bearer_token(token: str) -> dict:
    """Valida e decodifica JWT stub. Retorna claims."""
    ...

async def issue_token(tenant_id: str, client_id: str, scope: str) -> dict:
    """Emite token JWT stub com validade de 1 hora."""
    ...

async def validate_shared_key(
    account: str, signature: str, string_to_sign: str
) -> bool:
    """Validação permissiva em modo dev (sempre True)."""
    return True

def parse_resource_id(resource_id: str) -> dict:
    """
    Parseia ARM Resource ID:
    /subscriptions/{sub}/resourceGroups/{rg}/providers/{provider}/{type}/{name}
    Retorna dict com todos os componentes.
    """
    ...
```

---

## Atualização do Roteador (`ministack/core/router.py`)

Adicionar detecção de requisições Azure **antes** das AWS, identificando:

```python
def is_azure_request(scope: dict) -> bool:
    headers = dict(scope["headers"])
    path = scope["path"]
    
    # Headers Azure SDK
    if b"x-ms-date" in headers:         return True
    if b"x-ms-client-request-id" in headers: return True
    
    # Path prefixes Azure
    if path.startswith("/azure/"):        return True
    if path.startswith("/tenant/"):       return True   # Entra ID
    if path.startswith("/keyvault/"):     return True   # Key Vault
    if path.startswith("/subscriptions/"): return True  # ARM Management
    if path.startswith("/api/"):
        # Pode ser Azure Functions
        ...

    # Authorization header Bearer (vs AWS Signature v4)
    auth = headers.get(b"authorization", b"")
    if auth.startswith(b"Bearer "):       return True
    if auth.startswith(b"SharedKey "):    return True
    
    return False
```

---

## Suite de Testes (`tests/test_azure_services.py`)

Estrutura mínima esperada:

```python
import pytest
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient
from azure.keyvault.secrets import SecretClient
from azure.identity import ClientSecretCredential

BASE = "http://localhost:4566"
CRED = ClientSecretCredential(
    tenant_id="00000000-0000-0000-0000-000000000000",
    client_id="test", client_secret="test",
    authority=BASE
)

# Cobrir obrigatoriamente:
# test_blob_storage_crud          — create container, upload, download, delete
# test_blob_list_blobs            — list blobs em container
# test_entra_id_token             — obter Bearer token via client_credentials
# test_functions_invoke_python    — criar e invocar Azure Function Python
# test_functions_invoke_nodejs    — criar e invocar Azure Function Node.js
# test_cosmos_db_crud             — create db, container, insert, query, delete
# test_cosmos_db_sql_query        — SELECT via API SQL do Cosmos
# test_keyvault_secrets_crud      — set, get, list, delete secrets
# test_azure_sql_create_connect   — criar servidor, conectar via psycopg2
# test_cache_redis_create_connect — criar Redis, conectar via redis-py
# test_monitor_logs_ingest_query  — ingerir logs, executar query KQL básica
# test_arm_deployment_create      — deploy ARM template com Blob + Function
# test_service_bus_send_receive   — criar fila, send, receive, complete
# test_reset_endpoint             — POST /_ministack/reset limpa estado Azure
```

---

## Docker Compose Azure (`docker-compose.azure.yml`)

```yaml
version: "3.9"

services:
  azurestack:
    image: ministackorg/ministack:latest
    ports:
      - "4566:4566"     # Gateway principal (ARM, Functions, Cosmos, etc.)
      - "10000:10000"   # Azurite-compatible Blob Storage
      - "10001:10001"   # Azurite-compatible Queue Storage
      - "10002:10002"   # Azurite-compatible Table Storage
    environment:
      AZURE_MODE: "1"
      AZURE_TENANT_ID: "00000000-0000-0000-0000-000000000000"
      AZURE_SUBSCRIPTION_ID: "00000000-0000-0000-0000-000000000001"
      AZURE_LOCATION: "eastus"
      AZURE_STORAGE_ACCOUNT: "devstoreaccount1"
      PERSIST_STATE: "0"
      LOG_LEVEL: "INFO"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock  # Para Azure Functions e SQL containers
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4566/_ministack/health"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

---

## Restrições e Benchmarks Obrigatórios

- Imagem Docker final: < 350MB
- RAM em idle (AZURE_MODE=1): < 50MB
- Startup completo: < 2 segundos
- Cada serviço: arquivo Python isolado em `ministack/services/azure/`
- Função `reset()` obrigatória em cada handler
- Nenhuma dependência de runtime adicional além de `requirements.txt` atual
  (usar `azure-sdk-for-python` apenas como referência de tipos/contrato,
  nunca como dependência do servidor)
- Compatibilidade com Terraform `azurerm` provider v3.x e v4.x
- MIT License mantida

---

## Entregável — Pull Request com

1. Todo o diretório `ministack/services/azure/` com os 30 handlers
2. `ministack/core/auth_azure.py` — autenticação Bearer e Shared Key
3. `ministack/core/azure_resource_id.py` — parser de ARM Resource IDs
4. `ministack/core/router.py` — atualizado com detecção Azure
5. `ministack/app.py` — handlers Azure registrados no dispatcher
6. `tests/test_azure_services.py` — ≥ 14 testes nos 10 serviços prioritários
7. `docker-compose.azure.yml` — compose isolado para modo Azure
8. `README_AZURE.md` — quickstart com exemplos para SDK Python, Terraform e CLI
9. `pyproject.toml` — novo extra `azure` sem dependências de runtime adicionais
