# PROMPT: Extensão Multi-Cloud do MiniStack — Azure + Huawei Cloud

## 1. Contexto do Projeto Base

O MiniStack (<https://github.com/ministackorg/ministack>) é um emulador local
de AWS escrito em Python (ASGI/asyncio), com as seguintes características:

- **41 serviços AWS** emulados em porta única (padrão: 4566)
- **Arquitetura modular**: cada serviço é um arquivo Python independente em
  `ministack/services/`, com funções `async handle_request(request)` e `reset()`
- **Roteador central** em `ministack/core/router.py`: detecta o serviço-alvo via
  `X-Amz-Target` header, `Authorization` credential scope, `Action` query param,
  URL path pattern e Host header
- **Dispatcher** em `ministack/app.py`: registra `SERVICE_HANDLERS` e despacha
  para o handler correto
- **Helpers de resposta** em `ministack/core/responses.py`: XML, JSON e erros
- **Persistência opcional** via `ministack/core/persistence.py`
- **Lambda runtime** em `ministack/core/lambda_runtime.py` (subprocess warm pool)
- **Imagem Docker** ~250MB, startup <2s, ~40MB RAM idle

## 2. Objetivo

Estender o MiniStack para emular também serviços **Microsoft Azure** e
**Huawei Cloud**, criando um emulador **multi-cloud verdadeiro** na mesma
porta, mantendo compatibilidade total com:

- SDKs AWS existentes (boto3, AWS CLI, Terraform `aws` provider)
- SDK Azure Python (`azure-sdk-for-python`)
- SDK Huawei Cloud Python (`huaweicloudsdkcore`)
- Terraform providers: `azurerm` e `huaweicloud`

---

## 3. Arquitetura Multi-Cloud Proposta

### 3.1 Detecção de Provider no Router

Atualizar `ministack/core/router.py` para identificar o provider-alvo
**antes** do dispatch, com base em sinais de request:

```python
def detect_provider(scope: dict) -> str:
    """
    Retorna: "aws" | "azure" | "huawei"
    """
    headers = dict(scope.get("headers", []))
    path    = scope.get("path", "")

    # Azure — headers e path prefixes característicos
    if b"x-ms-client-request-id" in headers:
        return "azure"
    if b"x-ms-date" in headers:
        return "azure"
    if path.startswith(("/subscriptions/", "/providers/Microsoft.",
                        "/tenants", "/.default", "/oauth2/v2.0")):
        return "azure"

    # Huawei Cloud — headers e path prefixes característicos
    if b"x-auth-token" in headers:
        return "huawei"
    if b"x-sdk-date" in headers:
        return "huawei"
    if path.startswith(("/v3/auth/", "/v1.0/", "/v2/", "/v3/")):
        auth = headers.get(b"authorization", b"").decode()
        if "SDK-HMAC-SHA256" in auth:
            return "huawei"

    # Default: AWS
    return "aws"
```

### 3.2 Estrutura de Arquivos a Criar/Modificar

```
ministack/
├── core/
│   ├── router.py          ← MODIFICAR: adicionar detect_provider()
│   ├── auth_azure.py      ← NOVO: validação Bearer/MSAL tokens Azure
│   ├── auth_huawei.py     ← NOVO: validação AK/SK + token IAM Huawei
│   └── responses_cloud.py ← NOVO: helpers JSON para Azure/Huawei REST
├── services/
│   │── (existentes AWS, sem alteração)
│   ├── azure/
│   │   ├── __init__.py
│   │   ├── blob_storage.py     # Azure Blob Storage
│   │   ├── service_bus.py      # Azure Service Bus
│   │   ├── cosmos_db.py        # Azure Cosmos DB (NoSQL)
│   │   ├── functions.py        # Azure Functions
│   │   ├── key_vault.py        # Azure Key Vault
│   │   ├── monitor_logs.py     # Azure Monitor / Log Analytics
│   │   ├── event_hub.py        # Azure Event Hubs
│   │   ├── sql_db.py           # Azure SQL Database (real PG/MySQL)
│   │   ├── redis_cache.py      # Azure Cache for Redis
│   │   ├── iam_azure.py        # Azure AD / Entra ID (tokens)
│   │   ├── api_mgmt.py         # Azure API Management
│   │   ├── event_grid.py       # Azure Event Grid
│   │   ├── container_apps.py   # Azure Container Apps / ACI
│   │   ├── acr.py              # Azure Container Registry
│   │   └── arm_templates.py    # Azure Resource Manager (ARM/Bicep)
│   └── huawei/
│       ├── __init__.py
│       ├── obs.py              # Object Storage Service (S3-compatible)
│       ├── iam_hw.py           # IAM + token auth AK/SK
│       ├── smn.py              # Simple Message Notification
│       ├── dms.py              # Distributed Message Service
│       ├── functiongraph.py    # FunctionGraph (serverless)
│       ├── rds_hw.py           # RDS Huawei (real PG/MySQL container)
│       ├── dcs.py              # Distributed Cache Service (Redis)
│       ├── lts.py              # Log Tank Service
│       ├── aom.py              # Application Operations Management
│       ├── vpc_hw.py           # VPC Huawei
│       ├── ecs_hw.py           # Elastic Cloud Server
│       ├── apig.py             # API Gateway Huawei
│       ├── dis.py              # Data Ingestion Service
│       ├── kms_hw.py           # Key Management Service
│       └── csms.py             # Cloud Secret Management Service
├── app.py                      ← MODIFICAR: registrar handlers Azure/Huawei
tests/
├── test_services.py            ← existente (AWS), sem alteração
├── test_azure_services.py      ← NOVO
└── test_huawei_services.py     ← NOVO
docker-compose.yml              ← MODIFICAR: adicionar variáveis multi-cloud
docker-compose.azure.yml        ← NOVO: modo Azure isolado
docker-compose.huawei.yml       ← NOVO: modo Huawei isolado
README_AZURE.md                 ← NOVO
README_HUAWEI.md                ← NOVO
```

---

## 4. Mapeamento Completo de Serviços

### 4.1 AWS → Azure

| Serviço AWS | Equivalente Azure | API Base Path | SDK Python |
|-------------|------------------|---------------|------------|
| S3 | Azure Blob Storage | `/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{acct}/blobServices/default/containers` | `azure-storage-blob` |
| SQS | Azure Service Bus (queues) | `/subscriptions/{sub}/.../namespaces/{ns}/queues` | `azure-servicebus` |
| SNS | Azure Service Bus (topics) + Event Grid | `/subscriptions/{sub}/.../namespaces/{ns}/topics` | `azure-servicebus` |
| DynamoDB | Azure Cosmos DB (NoSQL API) | `/{account}.documents.azure.com/dbs/{db}/colls` | `azure-cosmos` |
| Lambda | Azure Functions | `/subscriptions/{sub}/.../sites/{fnApp}/functions` | `azure-functions` |
| RDS | Azure SQL Database | `/subscriptions/{sub}/.../servers/{srv}/databases` | `azure-mgmt-sql` |
| ElastiCache | Azure Cache for Redis | `/subscriptions/{sub}/.../redis/{name}` | `azure-mgmt-redis` |
| CloudWatch Logs | Azure Monitor / Log Analytics | `/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.OperationalInsights/workspaces` | `azure-monitor-query` |
| CloudWatch Metrics | Azure Monitor Metrics | `/subscriptions/{sub}/providers/Microsoft.Insights/metrics` | `azure-monitor-query` |
| Secrets Manager | Azure Key Vault (secrets) | `https://{vault}.vault.azure.net/secrets` | `azure-keyvault-secrets` |
| KMS | Azure Key Vault (keys) | `https://{vault}.vault.azure.net/keys` | `azure-keyvault-keys` |
| IAM/STS | Azure AD / Entra ID | `/tenants/{tenant}/oauth2/v2.0/token` | `azure-identity` |
| Kinesis | Azure Event Hubs | `/subscriptions/{sub}/.../namespaces/{ns}/eventhubs` | `azure-eventhub` |
| EC2 | Azure Virtual Machines | `/subscriptions/{sub}/.../virtualMachines` | `azure-mgmt-compute` |
| VPC | Azure Virtual Network | `/subscriptions/{sub}/.../virtualNetworks` | `azure-mgmt-network` |
| API Gateway | Azure API Management | `/subscriptions/{sub}/.../service/{name}/apis` | `azure-mgmt-apimanagement` |
| ECR | Azure Container Registry | `/subscriptions/{sub}/.../registries/{name}` | `azure-mgmt-containerregistry` |
| ECS | Azure Container Apps / ACI | `/subscriptions/{sub}/.../containerApps` | `azure-mgmt-appcontainers` |
| CloudFormation | ARM Templates / Bicep | `/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Resources/deployments` | `azure-mgmt-resource` |
| EventBridge | Azure Event Grid | `/subscriptions/{sub}/.../eventSubscriptions` | `azure-eventgrid` |
| Cognito | Azure AD B2C / Entra External ID | `/tenants/{tenant}/oauth2/v2.0/token` | `azure-identity` |

### 4.2 AWS → Huawei Cloud

| Serviço AWS | Equivalente Huawei | API Base Path | SDK Huawei |
|-------------|-------------------|---------------|------------|
| S3 | OBS (S3-compatible) | `/v1/{bucket}` | `huaweicloudsdkobs` |
| SQS | DMS (Distributed Message) | `/v1.0/{proj}/queues` | `huaweicloudsdkdms` |
| SNS | SMN (Simple Message Notification) | `/v2/{proj}/notifications/topics` | `huaweicloudsdksmn` |
| DynamoDB | GaussDB NoSQL / DCS | `/v2/{proj}/instances` | `huaweicloudsdkdcs` |
| Lambda | FunctionGraph | `/v2/{proj}/fgs/functions` | `huaweicloudsdkfunctiongraph` |
| RDS | RDS (GaussDB/MySQL/PG) | `/v3/{proj}/instances` | `huaweicloudsdkrds` |
| ElastiCache | DCS (Redis/Memcached) | `/v1.0/{proj}/instances` | `huaweicloudsdkdcs` |
| CloudWatch Logs | LTS (Log Tank Service) | `/v2/{proj}/groups` | `huaweicloudsdklts` |
| CloudWatch Metrics | AOM (App Ops Management) | `/v1/{proj}/ams/metrics` | `huaweicloudsdkaom` |
| Secrets Manager | DEW/CSMS | `/v1/{proj}/secrets` | `huaweicloudsdkdew` |
| KMS | KMS Huawei | `/v1.0/{proj}/kms/create-key` | `huaweicloudsdkkms` |
| IAM/STS | IAM Huawei | `/v3/auth/tokens` | `huaweicloudsdkiam` |
| Kinesis | DIS (Data Ingestion Service) | `/v2/{proj}/streams` | `huaweicloudsdkdis` |
| EC2 | ECS Huawei | `/v2/{proj}/cloudservers` | `huaweicloudsdkecs` |
| VPC | VPC Huawei | `/v1/{proj}/vpcs` | `huaweicloudsdkvpc` |
| API Gateway | APIG Huawei | `/v2/{proj}/apigw/instances` | `huaweicloudsdkapig` |
| ECR | SWR (Software Repository) | `/v2/manage/repos` | `huaweicloudsdkswr` |
| ECS containers | CCE (Cloud Container Engine) | `/api/v3/projects/{proj}/clusters` | `huaweicloudsdkcce` |
| CloudFormation | RFS (Resource Formation) | `/v1/{proj}/stacks` | `huaweicloudsdkrfs` |
| EventBridge | EG (Event Grid Huawei) | `/v1/{proj}/channels` | `huaweicloudsdkeg` |

---

## 5. Requisitos de Autenticação

### 5.1 Azure (`ministack/core/auth_azure.py`)

```python
# Suportar dois fluxos:
# 1. OAuth2 client_credentials (usado por azure-identity DefaultAzureCredential)
#    POST /tenants/{tenant_id}/oauth2/v2.0/token
#    Body: grant_type=client_credentials&client_id=...&client_secret=...
#    Response: {"access_token": "fake-token-xxx", "token_type": "Bearer", "expires_in": 3600}
# 2. Bearer token em Authorization header
#    Authorization: Bearer <token>
#    → aceitar qualquer token não-vazio como válido (modo emulador)

# Variáveis de ambiente:
# AZURE_SUBSCRIPTION_ID   = "00000000-0000-0000-0000-000000000000"
# AZURE_TENANT_ID         = "00000000-0000-0000-0000-000000000001"
# AZURE_CLIENT_ID         = "test"
# AZURE_CLIENT_SECRET     = "test"
# AZURE_RESOURCE_GROUP    = "ministack-rg"
```

### 5.2 Huawei Cloud (`ministack/core/auth_huawei.py`)

```python
# Suportar dois fluxos:
# 1. AK/SK com assinatura HMAC-SHA256
#    Authorization: SDK-HMAC-SHA256 Access=<ak>, SignedHeaders=..., Signature=<sig>
#    X-Sdk-Date: 20260412T095500Z
#    → validar formato, aceitar qualquer AK/SK em modo emulador
# 2. Token IAM (X-Auth-Token)
#    POST /v3/auth/tokens → retorna token no header X-Subject-Token
#    GET /v3/auth/tokens  → valida token existente

# Variáveis de ambiente:
# HUAWEICLOUD_SDK_AK      = "test"
# HUAWEICLOUD_SDK_SK      = "test"
# HUAWEICLOUD_PROJECT_ID  = "0000000000000000"
# HUAWEICLOUD_REGION      = "cn-north-4"
# HUAWEICLOUD_DOMAIN_ID   = "0000000000000000"
```

---

## 6. Implementação dos Handlers (Padrão de Código)

Cada handler deve seguir **exatamente** o padrão dos handlers AWS existentes:

```python
# ministack/services/azure/blob_storage.py
import json
from ministack.core.responses_cloud import json_response, error_response

_state = {}  # state isolado por handler

def reset():
    """Limpa estado (chamado por POST /_ministack/reset)"""
    _state.clear()

async def handle_request(request):
    """
    Ponto de entrada. request é um objeto com:
      - request.method: str
      - request.path: str
      - request.headers: dict
      - request.body: bytes (await request.body())
      - request.query_params: dict
    """
    method = request.method
    path   = request.path
    
    # Exemplo: PUT /{account}/default/containers/{container}
    if method == "PUT" and "/containers/" in path:
        container_name = path.split("/containers/")[-1].strip("/")
        _state.setdefault("containers", {})[container_name] = {"blobs": {}}
        return json_response({"id": container_name, "name": container_name}, status=201)

    # Exemplo: GET /{account}/default/containers
    if method == "GET" and path.endswith("/containers"):
        containers = [{"name": k} for k in _state.get("containers", {}).keys()]
        return json_response({"value": containers})

    return error_response(404, "ResourceNotFound", "Container operation not supported")
```

---

## 7. Variáveis de Ambiente Consolidadas

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `GATEWAY_PORT` | `4566` | Porta única para todos os clouds |
| `CLOUD_MODE` | `all` | `aws` \| `azure` \| `huawei` \| `all` |
| `AZURE_SUBSCRIPTION_ID` | `00000000-...` | Subscription ID emulada |
| `AZURE_TENANT_ID` | `00000000-...` | Tenant ID emulado |
| `AZURE_RESOURCE_GROUP` | `ministack-rg` | Resource Group padrão |
| `HUAWEICLOUD_SDK_AK` | `test` | Access Key Huawei |
| `HUAWEICLOUD_SDK_SK` | `test` | Secret Key Huawei |
| `HUAWEICLOUD_PROJECT_ID` | `0000000000000000` | Project ID padrão |
| `HUAWEICLOUD_REGION` | `cn-north-4` | Região Huawei padrão |
| `MINISTACK_ACCOUNT_ID` | `000000000000` | AWS Account ID (mantido) |
| `RDS_BASE_PORT` | `15432` | Base port para RDS/Azure SQL/Huawei RDS |
| `ELASTICACHE_BASE_PORT` | `16379` | Base port Redis (todos os clouds) |
| `PERSIST_STATE` | `0` | Persistência multi-cloud |

---

## 8. Compatibilidade com SDKs e Terraform

### 8.1 Azure SDK Python

```python
from azure.identity import ClientSecretCredential
from azure.storage.blob import BlobServiceClient

# Redirecionar para emulador via variável de ambiente
import os
os.environ["AZURE_STORAGE_CONNECTION_STRING"] = (
    "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
    "AccountKey=test;BlobEndpoint=http://localhost:4566/devstoreaccount1;"
)
# OU via endpoint_override:
client = BlobServiceClient(account_url="http://localhost:4566/devstoreaccount1",
                           credential="test")
```

### 8.2 Huawei Cloud SDK Python

```python
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkobs.v1 import ObsClient

credentials = BasicCredentials(ak="test", sk="test", project_id="0000000000000000")
client = ObsClient.new_builder() \
    .with_credentials(credentials) \
    .with_http_config({"endpoint_override": "http://localhost:4566"}) \
    .build()
```

### 8.3 Terraform — Provider Azure

```hcl
provider "azurerm" {
  features {}
  skip_provider_registration = true
  subscription_id = "00000000-0000-0000-0000-000000000000"
  tenant_id       = "00000000-0000-0000-0000-000000000001"
  client_id       = "test"
  client_secret   = "test"
  # endpoint override via ARM_ENDPOINT env var ou custom_endpoint
  environment = "public"
}
```

### 8.4 Terraform — Provider Huawei Cloud

```hcl
provider "huaweicloud" {
  region      = "cn-north-4"
  access_key  = "test"
  secret_key  = "test"
  auth_url    = "http://localhost:4566/v3"
  endpoints = {
    obs = "http://localhost:4566"
    rds = "http://localhost:4566"
  }
}
```

---

## 9. Endpoints Internos (manter + estender)

```bash
# Existentes (manter compatibilidade total)
GET  /_ministack/health
POST /_ministack/reset
POST /_ministack/config

# Novos — status por cloud
GET  /_azure/health         # status de todos os handlers Azure
POST /_azure/reset          # reset isolado Azure
GET  /_huawei/health        # status de todos os handlers Huawei
POST /_huawei/reset         # reset isolado Huawei
GET  /_multicloud/health    # status consolidado dos 3 clouds
```

---

## 10. Prioridade de Implementação

### Fase 1 — Infraestrutura base (obrigatório)

1. `ministack/core/router.py` — `detect_provider()` + dispatch multi-cloud
2. `ministack/core/auth_azure.py` — token OAuth2 + Bearer validation
3. `ministack/core/auth_huawei.py` — AK/SK HMAC + IAM token
4. `ministack/core/responses_cloud.py` — helpers JSON para Azure/Huawei
5. `ministack/app.py` — registro dos novos `SERVICE_HANDLERS`

### Fase 2 — Serviços de identidade (bloqueante para os demais)

6. `services/azure/iam_azure.py` — POST /oauth2/v2.0/token
2. `services/huawei/iam_hw.py` — POST /v3/auth/tokens

### Fase 3 — Storage e mensageria (maior uso em pipelines)

8. `services/azure/blob_storage.py` — CRUD completo de blobs e containers
2. `services/azure/service_bus.py` — queues e topics
3. `services/huawei/obs.py` — OBS (reutilizar handler S3 com header adaptation)
4. `services/huawei/smn.py` + `services/huawei/dms.py`

### Fase 4 — Compute e banco de dados

12. `services/azure/functions.py` — criar, invocar funções Python/Node.js
2. `services/azure/sql_db.py` — spin up real Postgres/MySQL via Docker
3. `services/azure/redis_cache.py` — spin up real Redis via Docker
4. `services/huawei/functiongraph.py`
5. `services/huawei/rds_hw.py` + `services/huawei/dcs.py`

### Fase 5 — Observabilidade, rede e IaC

17. `services/azure/monitor_logs.py` + `services/azure/event_hub.py`
2. `services/azure/arm_templates.py` (ARM/Bicep → provisioning emulado)
3. `services/huawei/lts.py` + `services/huawei/aom.py`
4. `services/huawei/vpc_hw.py` + `services/azure/vnet.py`

---

## 11. Testes Mínimos Exigidos

```python
# tests/test_azure_services.py — cobertura mínima:
# - test_azure_iam_get_token
# - test_azure_blob_create_container
# - test_azure_blob_put_get_object
# - test_azure_service_bus_send_receive
# - test_azure_cosmos_create_document
# - test_azure_functions_invoke
# - test_azure_key_vault_secret
# - test_azure_monitor_log_event

# tests/test_huawei_services.py — cobertura mínima:
# - test_huawei_iam_get_token
# - test_huawei_obs_create_bucket
# - test_huawei_obs_put_get_object
# - test_huawei_smn_create_topic_publish
# - test_huawei_functiongraph_invoke
# - test_huawei_rds_create_connect
# - test_huawei_dcs_redis_set_get
# - test_huawei_lts_send_logs
```

---

## 12. Restrições e Metas de Performance

- Imagem Docker final **< 350MB** (inclui handlers Azure + Huawei)
- RAM idle **< 60MB** com `CLOUD_MODE=all`
- Startup **< 2 segundos** (mantendo benchmark atual)
- Nenhum handler existente de AWS pode ser quebrado
- Código novo deve seguir o estilo Python existente (asyncio puro, sem frameworks extras)
- MIT License (manter)
- Compatibilidade com Terraform `azurerm` >= v3.x e `huaweicloud` >= v1.x

## 13. Entregáveis Finais (Pull Request)

1. Todos os arquivos listados na seção 3.2
2. `docker-compose.yml` atualizado (variáveis multi-cloud)
3. `docker-compose.azure.yml` e `docker-compose.huawei.yml`
4. `README_AZURE.md` com quickstart, mapeamento de serviços e exemplos SDK
5. `README_HUAWEI.md` com quickstart, mapeamento de serviços e exemplos SDK
6. `pyproject.toml` atualizado com extras `[azure]` e `[huawei]`
7. Suite de testes: `tests/test_azure_services.py` + `tests/test_huawei_services.py`
