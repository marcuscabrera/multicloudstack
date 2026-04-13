<p align="center">
  <img src="ministack_logo.png" alt="MiniStack — Free Open-Source Multi-Cloud Emulator" width="400"/>
</p>

<h1 align="center">MiniStack</h1>
<p align="center"><strong>Emulador local multi-cloud gratuito e open-source. Para sempre grátis.</strong></p>
<p align="center"><strong>Free, open-source multi-cloud local emulator. Free forever.</strong></p>
<p align="center">41 AWS · 30 Azure · 17 Huawei Cloud · 14 GCP = <strong>102 serviços</strong> em uma única porta · MIT licensed</p>

<p align="center">
  <a href="https://github.com/ministackorg/ministack/releases"><img src="https://img.shields.io/github/v/release/ministackorg/ministack" alt="GitHub release"></a>
  <a href="https://github.com/ministackorg/ministack/actions"><img src="https://img.shields.io/github/actions/workflow/status/ministackorg/ministack/ci.yml?branch=master" alt="Build"></a>
  <a href="https://hub.docker.com/r/ministackorg/ministack"><img src="https://img.shields.io/docker/pulls/ministackorg/ministack" alt="Docker Pulls"></a>
  <a href="https://hub.docker.com/r/ministackorg/ministack"><img src="https://img.shields.io/docker/image-size/ministackorg/ministack/latest" alt="Docker Image Size"></a>
  <a href="https://github.com/ministackorg/ministack/blob/master/LICENSE"><img src="https://img.shields.io/github/license/ministackorg/ministack" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.12-blue" alt="Python">
  <a href="https://github.com/ministackorg/ministack/stargazers"><img src="https://img.shields.io/github/stars/ministackorg/ministack" alt="GitHub stars"></a>
</p>

<p align="center">
  <a href="https://github.com/marcuscabrera/multicloudstack">Website</a> · <a href="https://hub.docker.com/r/ministackorg/ministack">Docker Hub</a> · <a href="https://www.linkedin.com/in/marcuscabrera">LinkedIn</a> · <a href="https://www.producthunt.com/products/ministack">Product Hunt</a> · <a href="doc/">Documentação</a>
</p>

---

## 📋 Descrição / Description

> **PT-BR:** O MiniStack é um emulador local multi-cloud que replica **102 serviços** de 4 provedores (AWS, Azure, Huawei Cloud e GCP) em uma única porta (4566). Compatível com SDKs oficiais, Terraform, CDK, Pulumi e CLIs oficiais. Alternativa gratuita ao LocalStack com imagem ~300MB, ~50MB RAM em idle e startup em menos de 2 segundos.
>
> **EN:** MiniStack is a multi-cloud local emulator that replicates **102 services** across 4 providers (AWS, Azure, Huawei Cloud, and GCP) on a single port (4566). Compatible with official SDKs, Terraform, CDK, Pulumi, and CLIs. A free alternative to LocalStack with a ~300MB image, ~50MB RAM at idle, and startup in under 2 seconds.

### Destaques / Highlights

| Recurso / Feature | Detalhe / Detail |
|---|---|
| **102 serviços** | 41 AWS · 30 Azure · 17 Huawei · 14 GCP |
| **Porta única** | Tudo em `localhost:4566` — detecção automática por cloud |
| **Infraestrutura real** | RDS/SQL sobe containers Postgres/MySQL reais; Redis real; Athena usa DuckDB; ECS roda containers Docker |
| **Footprint mínimo** | ~300MB Docker, ~50MB RAM idle, startup < 2s |
| **MIT License** | Livre para usar, modificar e distribuir |
| **Multi-tenancy** | Chaves de acesso de 12 dígitos = Account IDs isolados |

---

## 🚀 Instalação e Configuração / Installation & Setup

### Pré-requisitos / Prerequisites

- **Python 3.10+** ou **Docker** com Docker Compose
- `curl` (para health checks)
- Opcional: `awscli`, SDKs das clouds (`boto3`, `azure-*`, `huaweicloudsdk*`, `google-cloud-*`)

### Opção 1: Docker (Recomendado)

```bash
# Clone e suba todos os clouds
git clone https://github.com/ministackorg/ministack-huawei.git
cd ministack-huawei
docker compose up -d --build

# Ou use os scripts de início/parada
./bin/ministack-start              # Todos os clouds
./bin/ministack-start aws          # Apenas AWS
./bin/ministack-start azure,gcp    # Azure + GCP
./bin/ministack-stop               # Parar tudo
```

### Opção 2: Python (pip)

```bash
pip install -e .
# ou com dependências completas
pip install -e ".[full]"

# Iniciar
ministack
# ou
python -m uvicorn ministack.app:app --host 0.0.0.0 --port 4566
```

### Opção 3: Makefile

```bash
make build          # Build da imagem Docker
make run            # Build + start
make run-compose    # Via Docker Compose
make test           # Teste de integração completo
make health         # Verificar health
make logs           # Seguir logs
make stop           # Parar container
make clean          # Parar + remover imagem
make purge          # Limpar containers órfãos, volumes e dados S3
```

### Verificar Instalação / Verify Installation

```bash
# Health checks por cloud
curl http://localhost:4566/_ministack/health       # AWS
curl http://localhost:4566/_azure/health            # Azure
curl http://localhost:4566/_huawei/health           # Huawei Cloud
curl http://localhost:4566/_gcp/health              # GCP
curl http://localhost:4566/_multicloud/health       # Consolidado
```

### Modo Multi-Cloud / Multi-Cloud Mode

A variável `CLOUD_MODE` controla quais clouds estão ativas:

| `CLOUD_MODE` | Comportamento / Behavior |
|---|---|
| `all` (padrão/default) | Todas as 4 clouds — detecção automática por request |
| `aws` | Apenas AWS (comportamento original) |
| `azure` | Apenas Azure |
| `huawei` | Apenas Huawei Cloud |
| `gcp` | Apenas GCP |

```bash
# Exemplo: apenas AWS
docker run -p 4566:4566 -e CLOUD_MODE=aws ministackorg/ministack

# Exemplo: todos os clouds
docker compose up -d  # CLOUD_MODE=all é o padrão
```

### Variáveis de Ambiente / Environment Variables

| Variável | Padrão / Default | Descrição |
|----------|---------|-------------|
| `GATEWAY_PORT` | `4566` | Porta do gateway |
| `CLOUD_MODE` | `all` | `aws` / `azure` / `huawei` / `gcp` / `all` |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `S3_PERSIST` | `0` | `1` para persistir S3 em disco |
| `REDIS_HOST` | `redis` | Host Redis (ElastiCache/DCS) |
| `RDS_BASE_PORT` | `15432` | Porta base RDS/Azure SQL |
| `ELASTICACHE_BASE_PORT` | `16379` | Porta base Redis |
| `PERSIST_STATE` | `0` | `1` para persistir estado entre restarts |
| `AZURE_TENANT_ID` | `0000...0000` | Azure Tenant ID |
| `AZURE_SUBSCRIPTION_ID` | `0000...0001` | Azure Subscription ID |
| `AZURE_CLIENT_ID` | `test` | Service Principal ID |
| `AZURE_CLIENT_SECRET` | `test` | Service Principal Secret |
| `HUAWEICLOUD_SDK_AK` | `test` | Huawei Access Key |
| `HUAWEICLOUD_SDK_SK` | `test` | Huawei Secret Key |
| `HUAWEICLOUD_PROJECT_ID` | `0000000000000000` | Huawei Project ID |
| `HUAWEICLOUD_REGION` | `cn-north-4` | Huawei Region |
| `GCP_PROJECT_ID` | `ministack-emulator` | GCP Project ID |
| `GCP_REGION` | `us-central1` | GCP Region |
| `GCP_ZONE` | `us-central1-a` | GCP Zone |

---

## 💻 Exemplos de Uso / Usage Examples

### AWS — S3 + SQS + DynamoDB + Lambda

```bash
# AWS CLI
./bin/awslocal s3 mb s3://meu-bucket
./bin/awslocal s3 cp arquivo.txt s3://meu-bucket/
./bin/awslocal sqs create-queue --queue-name minha-fila
./bin/awslocal dynamodb list-tables
```

```python
import boto3

client = boto3.client("s3",
    endpoint_url="http://localhost:4566",
    aws_access_key_id="test",
    aws_secret_access_key="test",
    region_name="us-east-1",
)

client.create_bucket(Bucket="meu-bucket")
client.put_object(Bucket="meu-bucket", Key="hello.txt", Body=b"Hello AWS!")
obj = client.get_object(Bucket="meu-bucket", Key="hello.txt")
print(obj["Body"].read())  # b'Hello AWS!'
```

### Azure — Blob Storage + Entra ID + Service Bus

```bash
# Entra ID: obter token
curl -X POST "http://localhost:4566/tenant/00000000-0000-0000-0000-000000000000/oauth2/v2.0/token" \
  -d "grant_type=client_credentials&client_id=test&client_secret=test" \
  -H "Content-Type: application/x-www-form-urlencoded"

# Blob Storage: criar container
curl -X PUT "http://localhost:4566/azure/blob/devstoreaccount1/meu-container?restype=container" \
  -H "Authorization: Bearer test-token"
```

```python
from azure.storage.blob import BlobServiceClient

client = BlobServiceClient(
    account_url="http://localhost:4566/azure/blob/devstoreaccount1",
    credential="test"
)
container = client.create_container("meu-container")
container.upload_blob("hello.txt", b"Hello Azure!")
blob = container.download_blob("hello.txt")
print(blob.readall())  # b'Hello Azure!'
```

### Huawei Cloud — OBS + SMN + FunctionGraph

```bash
# OBS: criar bucket
curl -X PUT "http://localhost:4566/v1/meu-bucket" \
  -H "X-Auth-Token: test-token"

# SMN: criar tópico e publicar
curl -X POST "http://localhost:4566/v2/0000000000000000/notifications/topics" \
  -d '{"name": "meu-topico"}' \
  -H "Content-Type: application/json"
```

### GCP — Cloud Storage + Pub/Sub + BigQuery

```bash
# Metadata server
curl http://localhost:4566/computeMetadata/v1/project/project-id

# GCS: criar bucket
curl -X POST "http://localhost:4566/storage/v1/b" \
  -d '{"name": "meu-gcs-bucket"}' \
  -H "x-goog-api-client: test"

# Pub/Sub: criar tópico e publicar
curl -X PUT "http://localhost:4566/v1/projects/ministack-emulator/topics/meu-topico"
curl -X POST "http://localhost:4566/v1/projects/ministack-emulator/topics/meu-topico:publish" \
  -d '{"messages": [{"data": "SGVsbG8="}]}' \
  -H "x-goog-api-client: test"
```

### Terraform — AWS Provider

```hcl
provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    s3              = "http://localhost:4566"
    sqs             = "http://localhost:4566"
    dynamodb        = "http://localhost:4566"
    lambda          = "http://localhost:4566"
    iam             = "http://localhost:4566"
    # ... todos os endpoints
  }
}

resource "aws_s3_bucket" "dev" {
  bucket = "dev-bucket"
}
```

---

## 🛠️ Tecnologias e Frameworks / Technologies & Frameworks

| Camada / Layer | Tecnologia / Technology |
|---|---|
| **Linguagem** | Python 3.10, 3.11, 3.12 |
| **Servidor Web** | Uvicorn (ASGI) |
| **HTTP Parsing** | httptools |
| **Serialização** | PyYAML (CloudFormation), defusedxml (XML seguro) |
| **Banco de Dados (opcional)** | DuckDB (Athena), PostgreSQL (RDS), MySQL (RDS), Redis (ElastiCache/DCS) |
| **Containerização** | Docker SDK (Lambda, RDS, ECS, ElastiCache, Glue) |
| **Criptografia** | cryptography (KMS, ACM) |
| **DB Drivers** | psycopg2-binary (PostgreSQL), pymysql (MySQL) |
| **Build System** | setuptools |
| **Linting** | ruff (E, F, I rules) |
| **Testing** | pytest, pytest-xdist (parallel), pytest-cov |
| **CI/CD** | GitHub Actions (testes, PyPI, Docker Hub) |
| **SDKs Compatíveis** | boto3, azure-sdk-for-python, huaweicloudsdkcore, google-cloud-* |

---

## 🤝 Como Contribuir / How to Contribute

### Diretrizes de Código / Code Style Guidelines

- **Linter:** ruff com regras `E`, `F`, `I` selecionadas
- **Tamanho de linha:** 120 caracteres
- **Python alvo:** 3.10+
- **Cada serviço:** um arquivo Python independente em `ministack/services/`
- **Padrão de serviço:** função `async handle_request(method, path, headers, body, query_params)` + função `reset()` + `get_state()`/`restore_state()` para persistência
- **Estado:** use `AccountScopedDict` para isolamento multi-tenant

### Processo de Pull Request / Pull Request Process

1. **Fork** o repositório e crie uma branch (`git checkout -b feature/nome-da-feature`)
2. **Implemente** seguindo o padrão existente (um arquivo por serviço)
3. **Adicione testes** em `tests/test_nome_do_servico.py`
4. **Rode o linter:** `pip install ruff && ruff check ministack/`
5. **Rode os testes:** `pytest tests/ -v` (ou `make test` para integração)
6. **Commit** com mensagens claras (`git commit -m "feat: add new service XYZ"`)
7. **Push** para sua branch (`git push origin feature/nome-da-feature`)
8. **Abra o PR** com descrição das mudanças e testes realizados

### Adicionando um Novo Serviço / Adding a New Service

**AWS:**
1. Crie `ministack/services/nome_servico.py` com `handle_request()` e `reset()`
2. Registre em `SERVICE_HANDLERS` no `ministack/app.py`
3. Adicione padrões de detecção em `ministack/core/router.py`
4. Adicione testes em `tests/test_nome_servico.py`

**Azure:**
1. Crie `ministack/services/azure/nome_servico.py`
2. Registre nos handlers Azure em `app.py`
3. Adicione prefixo em `AZURE_SERVICE_PATTERNS` no `router.py`

**Huawei Cloud:**
1. Crie `ministack/services/huawei/nome_servico.py`
2. Registre nos handlers Huawei em `app.py`
3. Adicione prefixo em `HUAWEI_SERVICE_PATTERNS` no `router.py`

**GCP:**
1. Adicione handler em `ministack/services/gcp/gcp_services.py`
2. Crie wrapper `ministack/services/gcp/nome_servico.py`
3. Registre em `app.py` e adicione padrão em `GCP_SERVICE_PATTERNS`

### Documentação / Documentation

- Documentação detalhada na pasta `doc/`
- Veja `CONTRIBUTING.md` para guia completo

---

## 📜 Licença / License

**MIT License** — livre para usar, modificar e distribuir.

```
Copyright (c) 2026 MiniStack Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 📞 Contato e Suporte / Contact & Support

| Canal / Channel | Link |
|---|---|
| **GitHub Issues** | [https://github.com/ministackorg/ministack-huawei/issues](https://github.com/ministackorg/ministack-huawei/issues) |
| **GitHub Discussions** | [https://github.com/ministackorg/ministack-huawei/discussions](https://github.com/ministackorg/ministack-huawei/discussions) |
| **Website** | [https://ministack.org](https://ministack.org) |
| **Docker Hub** | [https://hub.docker.com/r/ministackorg/ministack](https://hub.docker.com/r/ministackorg/ministack) |
| **LinkedIn** | [https://www.linkedin.com/company/ministackorg/](https://www.linkedin.com/company/ministackorg/) |
| **Product Hunt** | [https://www.producthunt.com/products/ministack](https://www.producthunt.com/products/ministack) |
| **Security Issues** | Veja `SECURITY.md` |

---

## 🗺️ Roadmap

### Concluído / Done ✅

- [x] 41 serviços AWS emulados
- [x] 30 serviços Azure emulados
- [x] 17 serviços Huawei Cloud emulados
- [x] 14 serviços GCP emulados
- [x] Roteamento multi-cloud com detecção automática (`detect_provider()`)
- [x] Infraestrutura real (RDS containers, Redis, DuckDB, ECS Docker)
- [x] Multi-tenancy com AccountScopedDict
- [x] Warm worker pool para Lambda/FunctionGraph
- [x] Testes de integração para todas as clouds
- [x] Compatibilidade com Terraform (AWS, Azure, Huawei, GCP)
- [x] Persistência de estado opcional
- [x] Scripts de início/parada (`bin/ministack-start`, `bin/ministack-stop`)
- [x] Documentação completa em `doc/`

### Próximos Passos / Next Steps 🚧

- [ ] **CloudFormation completo** — Cobrir todos os resource types do AWS CloudFormation
- [ ] **ARM/Bicep completo** — Suporte completo a templates ARM e Bicep para Azure
- [ ] **Testcontainers oficial** — Integração com testcontainers-java, testcontainers-go
- [ ] **UI Dashboard** — Interface web para visualizar e gerenciar recursos emulados
- [ ] **Performance improvements** — Otimizar memória e startup time
- [ ] **Mais runtimes Lambda** — Java, Go, Ruby, .NET, custom runtimes
- [ ] **API Gateway completo** — Suporte completo a REST + HTTP APIs com authorizers
- [ ] **Step Functions completo** — Interpreter ASL completo com todos os estados
- [ ] **CI/CD integration examples** — Exemplos para GitHub Actions, GitLab CI, Jenkins
- [ ] **Helm chart** — Deploy em Kubernetes com Helm
- [ ] **OpenTelemetry** — Tracing e métricas integradas
- [ ] **Mock recording/playback** — Gravar interações reais e reproduzir localmente

---

## 📚 Documentação Completa / Full Documentation

Veja a pasta `doc/` para guias detalhados:

| Documento / Document | Descrição / Description |
|---|---|
| [doc/getting-started.md](doc/getting-started.md) | Instalação, configuração e primeiros passos |
| [doc/aws.md](doc/aws.md) | Guia completo dos 41 serviços AWS |
| [doc/azure.md](doc/azure.md) | Guia completo dos 30 serviços Azure |
| [doc/huawei.md](doc/huawei.md) | Guia completo dos 17 serviços Huawei Cloud |
| [doc/gcp.md](doc/gcp.md) | Guia completo dos 14 serviços GCP |
| [doc/multi-cloud.md](doc/multi-cloud.md) | Operações multi-cloud, detecção de provider |
| [doc/api-reference.md](doc/api-reference.md) | Referência completa de todos os endpoints |
| [doc/troubleshooting.md](doc/troubleshooting.md) | Problemas comuns e soluções |
