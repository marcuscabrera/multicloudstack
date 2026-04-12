# PROMPT: Adaptar MiniStack para emular serviços Huawei Cloud

## Contexto do Projeto

O MiniStack (<https://github.com/ministackorg/ministack>) é um emulador local
de AWS desenvolvido em Python (FastAPI/ASGI), com 41 serviços emulados em
uma única porta (4566). Cada serviço é um arquivo Python independente em
`ministack/services/`, registrado no roteador `ministack/core/router.py` e
no dispatcher `ministack/app.py`.

## Objetivo

Criar uma variante "MiniStack for Huawei Cloud" (nome sugerido:
`ministack-huawei` ou `huaweistack`) que emule localmente os principais
serviços da Huawei Cloud, mantendo a mesma arquitetura modular, leveza
e compatibilidade com SDKs oficiais (huaweicloudsdkcore / Python).

## Mapeamento de Serviços AWS → Huawei Cloud

Implemente os seguintes mapeamentos de equivalência:

| Serviço AWS (MiniStack) | Equivalente Huawei Cloud | SDK Huawei | Porta de API |
|------------------------|--------------------------|------------|-------------|
| S3                     | OBS (Object Storage)     | huaweicloudsdkobs | /v1/{bucket} |
| SQS                    | DMS (Distributed Message) | huaweicloudsdkdms | /v1.0/{proj}/queues |
| SNS                    | SMN (Simple Message)     | huaweicloudsdksmn | /v2/{proj}/notifications |
| DynamoDB               | GaussDB NoSQL / DCS      | huaweicloudsdkdcs | /v2/{proj}/instances |
| Lambda                 | FunctionGraph            | huaweicloudsdkfunctiongraph | /v2/{proj}/fgs/functions |
| RDS                    | RDS (GaussDB/MySQL/PG)   | huaweicloudsdkrds | /v3/{proj}/instances |
| ECS                    | CCE / SWR containers     | huaweicloudsdkcce | /api/v3/projects/{proj}/clusters |
| CloudWatch Logs        | LTS (Log Tank Service)   | huaweicloudsdklts | /v2/{proj}/groups |
| CloudWatch Metrics     | AOM (App Ops Mgmt)       | huaweicloudsdkaom | /v1/{proj}/ams/metrics |
| Secrets Manager        | DEW/CSMS                 | huaweicloudsdkdew | /v1/{proj}/secrets |
| KMS                    | KMS Huawei               | huaweicloudsdkkms | /v1.0/{proj}/kms |
| IAM/STS                | IAM Huawei               | huaweicloudsdkiam | /v3/auth/tokens |
| ElastiCache            | DCS (Redis/Memcached)    | huaweicloudsdkdcs | /v1.0/{proj}/instances |
| Kinesis                | DIS (Data Ingestion)     | huaweicloudsdkdis | /v2/{proj}/streams |
| EC2                    | ECS Huawei               | huaweicloudsdkecs | /v2/{proj}/cloudservers |
| API Gateway            | APIG Huawei              | huaweicloudsdkapig | /v2/{proj}/apigw |
| CloudFormation         | RFS (Resource Formation) | huaweicloudsdkrfs | /v1/{proj}/stacks |
| SES                    | SES Huawei / SMN email   | huaweicloudsdksmn | /v2/{proj}/notifications |
| VPC/Subnet/SG          | VPC Huawei               | huaweicloudsdkvpc | /v1/{proj}/vpcs |

## Requisitos Técnicos de Implementação

### 1. Autenticação

- Suportar autenticação AK/SK (Access Key / Secret Key) da Huawei Cloud
- Header: `X-Auth-Token` ou assinatura HMAC-SHA256 (padrão Huawei)
- Variáveis de ambiente: `HUAWEICLOUD_SDK_AK`, `HUAWEICLOUD_SDK_SK`,
  `HUAWEICLOUD_PROJECT_ID`, `HUAWEICLOUD_REGION`
- Endpoint de token: `POST /v3/auth/tokens` (IAM)
- Compatibilidade com `huaweicloudsdkcore.auth.credentials.BasicCredentials`

### 2. Estrutura de URLs

As URLs Huawei Cloud seguem o padrão:

```
https://{service}.{region}.myhuaweicloud.com/{api_version}/{project_id}/{resource}
```

No emulador, substituir por:

```
http://localhost:4566/{service_prefix}/{api_version}/{project_id}/{resource}
```

Implementar roteamento baseado no path prefix de cada serviço.

### 3. Roteador Principal (`ministack/core/router.py`)

Adaptar a lógica de detecção para identificar chamadas Huawei Cloud:

- Verificar header `X-Auth-Token` ou `Authorization: HMAC-SHA256`  
- Verificar prefixo de path: `/v1.0/`, `/v2/`, `/v3/`
- Verificar header `X-Sdk-Date` (presente nas requisições Huawei SDK)

### 4. Serviços Prioritários (implementar primeiro)

1. **OBS** — Protocolo compatível com S3 (Huawei OBS usa API S3-compatible)
   - Reaproveitamento direto do handler S3 existente
   - Adicionar headers específicos: `x-obs-request-id`, `x-obs-id-2`
2. **IAM** — Token de autenticação (necessário para todos os outros serviços)
3. **SMN** — Notificações (equivalente SNS)
4. **FunctionGraph** — Funções serverless (equivalente Lambda)
5. **RDS** — Banco relacional (spin up real Postgres/MySQL como no MiniStack)
6. **DCS** — Cache Redis (reaproveitamento do handler ElastiCache)
7. **LTS** — Logs (equivalente CloudWatch Logs)
8. **VPC** — Redes virtuais (equivalente VPC/EC2 networking)

### 5. Estrutura de Arquivos a Criar/Modificar

```
ministack/
├── services/
│   ├── obs.py          # Object Storage Service (S3-compatible)
│   ├── iam_hw.py       # IAM Huawei (token auth)
│   ├── smn.py          # Simple Message Notification
│   ├── dms.py          # Distributed Message Service
│   ├── functiongraph.py # FunctionGraph (serverless)
│   ├── rds_hw.py       # RDS Huawei (reusa lógica do rds.py)
│   ├── dcs.py          # Distributed Cache Service  
│   ├── lts.py          # Log Tank Service
│   ├── aom.py          # Application Operations Management
│   ├── vpc_hw.py       # VPC Huawei
│   ├── ecs_hw.py       # Elastic Cloud Server
│   ├── apig.py         # API Gateway Huawei
│   ├── dis.py          # Data Ingestion Service
│   ├── kms_hw.py       # Key Management Service
│   └── csms.py         # Cloud Secret Management Service
├── core/
│   ├── router.py       # Atualizar para detectar Huawei SDK calls
│   └── auth_huawei.py  # Novo: validação AK/SK e token IAM
└── app.py              # Registrar os novos handlers
```

### 6. Endpoints Internos (manter compatibilidade)

```
GET  http://localhost:4566/_ministack/health
POST http://localhost:4566/_ministack/reset
POST http://localhost:4566/_ministack/config
```

Adicionar:

```
GET  http://localhost:4566/_huawei/health   # Status dos serviços Huawei
POST http://localhost:4566/_huawei/reset    # Reset isolado Huawei
```

### 7. Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `HUAWEICLOUD_SDK_AK` | `test` | Access Key emulada |
| `HUAWEICLOUD_SDK_SK` | `test` | Secret Key emulada |
| `HUAWEICLOUD_PROJECT_ID` | `0000000000000000` | Project ID padrão |
| `HUAWEICLOUD_REGION` | `cn-north-4` | Região padrão |
| `GATEWAY_PORT` | `4566` | Mesma porta (manter compatibilidade) |
| `HUAWEI_MODE` | `0` | Set `1` para ativar modo Huawei Cloud |

### 8. Compatibilidade com SDK Python Huawei

O emulador deve funcionar transparentemente com o SDK oficial:

```python
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkobs.v1 import ObsClient

credentials = BasicCredentials(ak="test", sk="test", project_id="000000")

client = ObsClient.new_builder() \
    .with_credentials(credentials) \
    .with_region("cn-north-4") \
    .with_http_config({"endpoint_override": "http://localhost:4566"}) \
    .build()

# Deve funcionar exatamente como na Huawei Cloud real
response = client.list_buckets()
```

### 9. Testes

Criar `tests/test_huawei_services.py` com testes para cada serviço emulado,
seguindo o padrão existente em `tests/test_services.py`. Usar fixtures do
`tests/conftest.py` para setup/teardown.
Prioridade mínima de cobertura:

- OBS: CRUD completo de objetos e buckets
- IAM: obtenção e validação de tokens
- FunctionGraph: criação e invocação de funções Python/Node.js
- RDS: criação de instância e conexão real via psycopg2
- DCS: criação de cache cluster e acesso via redis-py
- LTS: criação de grupo de logs e envio de eventos
- SMN: criação de tópico e publicação de mensagens

### 10. Docker e Deploy

Atualizar `docker-compose.yml` e `Dockerfile` para suportar modo dual:

- Modo AWS (padrão, `HUAWEI_MODE=0`)
- Modo Huawei Cloud (`HUAWEI_MODE=1`)
- Modo híbrido (`HUAWEI_MODE=2`, emula os dois simultaneamente em paths diferentes)

## Restrições e Boas Práticas

- Manter leveza: imagem Docker alvo < 300MB, RAM idle < 50MB
- Cada serviço deve ser um arquivo Python independente (padrão atual)
- Sem dependências externas além do já presente em `requirements.txt` e
  `huaweicloudsdkcore` (apenas para referência de tipos, não como runtime)
- Compatibilidade total com Terraform provider `huaweicloud` v1.x
- Startup < 2 segundos (manter benchmark atual)
- MIT License (manter)

## Entregável Final

Pull request com:

1. Todos os arquivos de serviço Huawei listados acima
2. `ministack/core/auth_huawei.py` — módulo de autenticação AK/SK
3. `ministack/core/router.py` — atualizado para roteamento dual
4. `tests/test_huawei_services.py` — suite de testes cobrindo os 8 serviços prioritários
5. `README_HUAWEI.md` — documentação de uso com exemplos boto3-style para SDK Huawei
6. `docker-compose.huawei.yml` — compose file para modo Huawei isolado
