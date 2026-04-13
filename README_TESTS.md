# MiniStack Multi-Cloud Test Suite Documentation

## Overview

Esta suite de testes funcional valida **4 providers cloud simultaneamente**:
- **AWS** (41 serviços nativos)
- **Azure** (Blob Storage, Service Bus, Functions, CosmosDB, Key Vault, etc.)
- **GCP** (GCS, Pub/Sub, Cloud Functions, Cloud SQL, BigQuery, etc.)
- **Huawei Cloud** (OBS, SMN, FunctionGraph, RDS Huawei, DCS, etc.)

## Estrutura dos Testes

```
tests/
├── conftest.py                   # fixtures AWS existentes (SEM ALTERAÇÃO)
├── test_*.py                     # testes AWS individuais (1188 testes)
├── test_multicloud/              # NOVO: testes multi-cloud
│   ├── conftest.py               # fixtures específicas multi-cloud
│   ├── test_auth.py              # autenticação de todos os 4 clouds
│   ├── test_storage.py           # S3/GCS/Blob/OBS — CRUD end-to-end
│   ├── test_messaging.py         # SQS+PubSub+ServiceBus+SMN
│   ├── test_serverless.py        # Lambda+Functions+FunctionGraph
│   └── ...                       # mais arquivos de teste
docker/
├── docker-compose.test.yml       # stack completa com todos os 4 clouds
├── init_aws.sh                   # scripts de setup AWS
├── init_gcp.sh                   # metadata server GCP + buckets iniciais
├── init_azure.sh                 # resource groups + storage accounts
└── init_huawei.sh                # OBS buckets + SMN topics
```

## Instalação

### 1. Instalar dependências de teste

```bash
pip install -r requirements-test.txt
```

### 2. Iniciar MiniStack com Docker Compose

```bash
docker compose -f docker/docker-compose.test.yml up -d
```

### 3. Aguardar inicialização

```bash
# Verificar saúde do MiniStack
curl http://localhost:4566/_ministack/health
```

## Execução dos Testes

### Todos os testes multi-cloud

```bash
pytest tests/test_multicloud/ -v
```

### Testes paralelos (rápido)

```bash
pytest tests/test_multicloud/ -n auto -v
```

### Testes específicos por provider

```bash
# Apenas AWS
pytest tests/test_multicloud/ -m aws -v

# Apenas Azure
pytest tests/test_multicloud/ -m azure -v

# Apenas GCP
pytest tests/test_multicloud/ -m gcp -v

# Apenas Huawei
pytest tests/test_multicloud/ -m huawei -v
```

### Testes de regressão AWS (existentes)

```bash
pytest tests/test_services.py -v  # deve continuar 100% verde
```

### Com cobertura de código

```bash
pytest tests/ --cov=ministack --cov-report=html
```

## Fixtures Disponíveis

### AWS
- `s3_client` - boto3 S3 client
- `lambda_client` - boto3 Lambda client
- `sqs` - boto3 SQS client
- `aws_credentials` - dict com credenciais AWS

### GCP
- `gcp_headers` - headers para requisições HTTP GCP
- `gcp_project` - project ID configurado

### Azure
- `azure_headers` - headers para requisições HTTP Azure
- `azure_subscription_id` - subscription ID configurado

### Huawei
- `huawei_headers` - headers para requisições HTTP Huawei
- `huawei_project_id` - project ID configurado

### Utilitários
- `http_request` - função genérica para requisições HTTP
- `unique_suffix` - gera suffix único para nomes de recursos

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `MINISTACK_ENDPOINT` | `http://localhost:4566` | Endpoint do MiniStack |
| `AWS_ACCESS_KEY_ID` | `test` | Access key AWS |
| `AWS_SECRET_ACCESS_KEY` | `test` | Secret key AWS |
| `GCP_PROJECT_ID` | `ministack-test` | Project ID GCP |
| `AZURE_SUBSCRIPTION_ID` | `00000000-...` | Subscription ID Azure |
| `HUAWEICLOUD_PROJECT_ID` | `0000000000000000` | Project ID Huawei |

## KPIs de Sucesso

| Métrica | Target |
|---------|--------|
| Total de testes | >500 (100+ por cloud) |
| Tempo total | <5min (com parallelização) |
| Cobertura handlers novos | 100% |
| Regressão AWS | 0% (1188 testes existentes) |
| Taxa de falha em CI | <0.1% |
| RAM peak (todos os clouds) | <80MB |
| Startup time | <3s |

## Troubleshooting

### MiniStack não inicia

```bash
# Verificar logs do container
docker logs ministack

# Reiniciar stack
docker compose -f docker/docker-compose.test.yml down
docker compose -f docker/docker-compose.test.yml up -d
```

### Testes falhando por timeout

Aumentar timeout nas requisições:
```python
def _request(method, path, data=None, headers=None):
    # ... 
    with urllib.request.urlopen(req, timeout=30) as resp:  # aumentar para 30s
```

### Recursos não isolados entre testes

Verificar se o reset está funcionando:
```bash
curl -X POST http://localhost:4566/_multicloud/reset
```

## Integração CI/CD

Exemplo GitHub Actions:

```yaml
name: Multi-Cloud Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - uses: actions/setup-python@v5
      with:
        python-version: '3.12'
      
    - run: pip install -r requirements-test.txt
    
    - name: Start MiniStack + Test
      run: |
        docker compose -f docker/docker-compose.test.yml up -d
        sleep 10  # wait for startup
        pytest tests/test_multicloud/ -v -n auto --cov=ministack
```

## Contribuição

1. Criar novo arquivo de teste em `tests/test_multicloud/`
2. Usar fixtures do `conftest.py` para consistência
3. Adicionar marker apropriado (`@pytest.mark.aws`, etc.)
4. Garantir isolamento entre testes (usar `unique_suffix`)
5. Executar testes localmente antes de commit

## Licença

MIT License - ver LICENSE no repositório principal.
