# API Reference

## Internal Endpoints

MiniStack exposes internal endpoints for health checks, state management, and runtime configuration.

### Health Endpoints

#### AWS Health

```
GET /_ministack/health
```

Response:
```json
{
  "services": {
    "s3": "available",
    "sqs": "available",
    "dynamodb": "available",
    "...": "available"
  },
  "edition": "light",
  "version": "3.0.0.dev"
}
```

#### Azure Health

```
GET /_azure/health
```

Response:
```json
{
  "services": {
    "azure_blob": "available",
    "entra_id": "available",
    "azure_service_bus": "available",
    "...": "available"
  },
  "mode": "all"
}
```

#### Huawei Cloud Health

```
GET /_huawei/health
```

Response:
```json
{
  "services": {
    "obs": "available",
    "iam_hw": "available",
    "smn": "available",
    "...": "available"
  },
  "mode": "all"
}
```

#### GCP Health

```
GET /_gcp/health
```

Response:
```json
{
  "services": {
    "gcp_storage": "available",
    "gcp_pubsub": "available",
    "gcp_functions": "available",
    "...": "available"
  },
  "mode": "all"
}
```

#### Multi-Cloud Health

```
GET /_multicloud/health
```

Response:
```json
{
  "cloud_mode": "all",
  "aws_services": 41,
  "azure_services": 30,
  "huawei_services": 17,
  "gcp_services": 14,
  "status": "available"
}
```

#### LocalStack Compatibility

```
GET /_localstack/health
GET /health
```

Same format as `/_ministack/health`.

### Reset Endpoints

Reset all state for a specific cloud. Useful between test runs.

```
POST /_ministack/reset     # AWS
POST /_azure/reset          # Azure
POST /_huawei/reset         # Huawei Cloud
POST /_gcp/reset            # GCP
```

Response:
```json
{"reset": "ok", "scope": "aws|azure|huawei|gcp"}
```

### Runtime Configuration

```
POST /_ministack/config
Content-Type: application/json
```

Allowed keys:
- `athena.ATHENA_ENGINE` — SQL engine (`auto`, `duckdb`, `mock`)
- `athena.ATHENA_DATA_DIR` — Athena data directory
- `stepfunctions._sfn_mock_config` — Step Functions mock config
- `lambda_svc.LAMBDA_EXECUTOR` — Lambda executor mode (`local` or `docker`)

Example:
```bash
curl -X POST http://localhost:4566/_ministack/config \
  -H "Content-Type: application/json" \
  -d '{"lambda_svc.LAMBDA_EXECUTOR": "docker"}'
```

Response:
```json
{"applied": {"lambda_svc.LAMBDA_EXECUTOR": "docker"}}
```

## Authentication Endpoints

### Azure Entra ID

#### OAuth2 Token

```
POST /tenant/{tenant_id}/oauth2/v2.0/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&client_id={client_id}&client_secret={secret}&scope=https://management.azure.com/.default
```

Response:
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "ext_expires_in": 3600
}
```

#### OIDC Discovery

```
GET /tenant/{tenant_id}/.well-known/openid-configuration
```

#### JWKS

```
GET /tenant/{tenant_id}/discovery/v2.0/keys
```

### Huawei IAM

#### Token

```
POST /v3/auth/tokens
Content-Type: application/json

{"auth": {"methods": ["token"], "scope": {"project": {"id": "..."}}}}
```

Response header: `X-Subject-Token: <token-id>`

### GCP Metadata Server

```
GET /computeMetadata/v1/project/project-id
GET /computeMetadata/v1/instance/service-accounts/default/email
GET /computeMetadata/v1/instance/service-accounts/default/token
GET /computeMetadata/v1/instance/zone
GET /computeMetadata/v1/instance/hostname
GET /computeMetadata/v1/instance/name
```

## Cloud-Specific API Paths

### AWS

Standard AWS API paths via AWS SDK conventions:
- S3: `/{bucket}/{key}` or virtual-hosted `http://{bucket}.localhost/{key}`
- SQS: `/{account_id}/{queue_name}` or `?Action=SendMessage`
- DynamoDB: JSON protocol with `X-Amz-Target` header
- Lambda: `/2015-03-31/functions/{name}`
- EC2: `?Action=DescribeInstances`
- RDS: `?Action=CreateDBInstance`
- CloudFormation: `?Action=CreateStack`

### Azure

- Blob Storage: `/azure/blob/{account}/{container}/{blob}?restype=container`
- Service Bus: `/subscriptions/{sub}/.../namespaces/{ns}/queues/{q}`
- Functions: `/api/{funcName}` (invoke), `/v1/projects/{proj}/.../functions` (CRUD)
- Cosmos DB: `/azure/cosmos/{account}/dbs/{db}/colls/{coll}/docs`
- Key Vault: `/keyvault/{vault}/secrets/{name}`
- ARM: `/subscriptions/{sub}/resourceGroups/{rg}/providers/{provider}/{type}/{name}`

### Huawei Cloud

- OBS: `/v1/{bucket}/{key}`
- IAM: `/v3/auth/tokens`
- SMN: `/v2/{proj}/notifications/topics/{name}/publish`
- FunctionGraph: `/v2/{proj}/fgs/functions/{name}`
- RDS: `/v3/{proj}/instances`
- DCS: `/v1.0/{proj}/instances` or `/v2/{proj}/instances`
- LTS: `/v2/{proj}/groups`, `/streams`, `/logs`
- VPC: `/v1/{proj}/vpcs`

### GCP

- GCS: `/storage/v1/b/{bucket}/o/{object}`
- Pub/Sub: `/v1/projects/{proj}/topics/{name}:publish`
- BigQuery: `/bigquery/v2/projects/{proj}/datasets`, `/queries`
- Cloud SQL: `/sql/v1beta4/projects/{proj}/instances`
- Cloud Functions: `/v1/projects/{proj}/locations/{loc}/functions/{name}`
- Metadata: `/computeMetadata/v1/...`
- Secret Manager: `/v1/projects/{proj}/secrets/{name}`
- KMS: `/v1/projects/{proj}/locations/{loc}/keyRings/{name}/cryptoKeys/{key}:encrypt`

## Response Headers

All responses include cloud-specific request ID headers:

| Cloud | Request ID Header |
|-------|------------------|
| AWS | `x-amzn-requestid`, `x-amz-request-id`, `x-amz-id-2` |
| Azure | `x-ms-request-id` |
| Huawei Cloud | `x-request-id`, `x-obs-request-id` |
| GCP | Standard HTTP headers |

## CORS Headers

All endpoints return permissive CORS headers for browser-based SDKs:

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, HEAD, OPTIONS, PATCH
Access-Control-Allow-Headers: *
Access-Control-Expose-Headers: *
Access-Control-Max-Age: 86400
```

## Error Responses

### AWS (JSON)
```json
{"__type": "ResourceNotFound", "message": "The specified resource does not exist"}
```

### AWS (XML)
```xml
<ErrorResponse>
  <Error>
    <Type>Sender</Type>
    <Code>NoSuchBucket</Code>
    <Message>The specified bucket does not exist</Message>
  </Error>
  <RequestId>...</RequestId>
</ErrorResponse>
```

### Azure
```json
{"error": {"code": "ResourceNotFound", "message": "The resource does not exist"}}
```

### Huawei Cloud
```json
{"error_code": "SVC.0001", "error_msg": "Resource not found", "request_id": "..."}
```

### GCP
```json
{"error": {"code": 404, "message": "Resource not found"}}
```
