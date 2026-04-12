# GCP Services

## Overview

MiniStack emulates **14 GCP services** on port `4566`. Services are detected via `x-goog-*` headers or `/storage/v1/`, `/pubsub/v1/`, `/bigquery/v/`, `/computeMetadata/` path prefixes.

## Quick Start

```bash
./bin/ministack-start gcp

# Verify
curl http://localhost:4566/_gcp/health
```

## Metadata Server

GCP's metadata server is emulated at `/computeMetadata/v1/`:

```bash
# Project ID
curl http://localhost:4566/computeMetadata/v1/project/project-id

# Service account email
curl http://localhost:4566/computeMetadata/v1/instance/service-accounts/default/email

# Access token
curl http://localhost:4566/computeMetadata/v1/instance/service-accounts/default/token

# Zone
curl http://localhost:4566/computeMetadata/v1/instance/zone
```

**Python:**

```python
import urllib.request

# Get metadata
req = urllib.request.Request(
    "http://localhost:4566/computeMetadata/v1/project/project-id",
    headers={"Metadata-Flavor": "Google"}
)
with urllib.request.urlopen(req) as resp:
    print(resp.read().decode())  # ministack-emulator
```

## GCS (Cloud Storage)

### Create Bucket

```bash
curl -X POST "http://localhost:4566/storage/v1/b" \
  -d '{"name": "my-bucket"}' \
  -H "x-goog-api-client: test" \
  -H "Content-Type: application/json"
```

### List Buckets

```bash
curl "http://localhost:4566/storage/v1/b" \
  -H "x-goog-api-client: test"
```

### Upload Object

```bash
curl -X POST "http://localhost:4566/storage/v1/b/my-bucket/o" \
  -d '{"name": "hello.txt"}' \
  -H "x-goog-api-client: test" \
  -H "Content-Type: application/json"
```

### List Objects

```bash
curl "http://localhost:4566/storage/v1/b/my-bucket/o" \
  -H "x-goog-api-client: test"
```

## Pub/Sub

### Create Topic

```bash
curl -X PUT "http://localhost:4566/v1/projects/ministack-emulator/topics/my-topic" \
  -H "x-goog-api-client: test"
```

### Publish Message

```bash
curl -X POST "http://localhost:4566/v1/projects/ministack-emulator/topics/my-topic:publish" \
  -d '{"messages": [{"data": "SGVsbG8="}]}' \
  -H "x-goog-api-client: test" \
  -H "Content-Type: application/json"
```

### Pull Message

```bash
curl -X POST "http://localhost:4566/v1/projects/ministack-emulator/subscriptions/my-sub:pull" \
  -d '{}' \
  -H "x-goog-api-client: test" \
  -H "Content-Type: application/json"
```

## Cloud Functions

### Create Function

```bash
curl -X POST "http://localhost:4566/v1/projects/ministack-emulator/locations/us-central1/functions/my-fn" \
  -d '{"entryPoint": "handler", "runtime": "python311"}' \
  -H "x-goog-api-client: test" \
  -H "Content-Type: application/json"
```

### Invoke Function

```bash
curl -X POST "http://localhost:4566/gcp/fn/my-fn" \
  -d '{"name": "GCP"}' \
  -H "Content-Type: application/json"
```

## BigQuery

### Create Dataset

```bash
curl -X POST "http://localhost:4566/bigquery/v2/projects/ministack-emulator/datasets" \
  -d '{"datasetReference": {"projectId": "ministack-emulator", "datasetId": "my_dataset"}}' \
  -H "x-goog-api-client: test" \
  -H "Content-Type: application/json"
```

### Run Query

```bash
curl -X POST "http://localhost:4566/bigquery/v2/projects/ministack-emulator/queries" \
  -d '{"query": "SELECT 1 as num"}' \
  -H "x-goog-api-client: test" \
  -H "Content-Type: application/json"
```

## Cloud SQL

```bash
curl -X POST "http://localhost:4566/sql/v1beta4/projects/ministack-emulator/instances" \
  -d '{"name": "my-sql", "databaseVersion": "POSTGRES_14"}' \
  -H "x-goog-api-client: test" \
  -H "Content-Type: application/json"
```

## Secret Manager

### Create Secret

```bash
curl -X POST "http://localhost:4566/v1/projects/ministack-emulator/secrets:my-secret" \
  -H "x-goog-api-client: test"
```

### Add Version

```bash
curl -X POST "http://localhost:4566/v1/projects/ministack-emulator/secrets/my-secret:addVersion" \
  -H "x-goog-api-client: test"
```

### Access Secret

```bash
curl "http://localhost:4566/v1/projects/ministack-emulator/secrets/my-secret/versions/latest:access" \
  -H "x-goog-api-client: test"
```

## Cloud KMS

### Create Key Ring

```bash
curl -X POST "http://localhost:4566/v1/projects/ministack-emulator/locations/us-central1/keyRings:my-kr" \
  -H "x-goog-api-client: test"
```

### Create Crypto Key

```bash
curl -X POST "http://localhost:4566/v1/projects/ministack-emulator/locations/us-central1/keyRings/my-kr/cryptoKeys" \
  -d '{"name": "my-key"}' \
  -H "x-goog-api-client: test" \
  -H "Content-Type: application/json"
```

## Cloud IAM

### Create Service Account

```bash
curl -X POST "http://localhost:4566/v1/projects/ministack-emulator/serviceAccounts" \
  -d '{"accountId": "my-service-account"}' \
  -H "x-goog-api-client: test" \
  -H "Content-Type: application/json"
```

## Complete Service List

| Service | API Path | Status |
|---------|----------|--------|
| GCS | `/storage/v1/b` | ✅ |
| Pub/Sub | `/v1/projects/{proj}/topics` | ✅ |
| Cloud Functions | `/v1/projects/{proj}/locations/{loc}/functions` | ✅ |
| BigQuery | `/bigquery/v2/projects/{proj}` | ✅ |
| Cloud SQL | `/sql/v1beta4/projects/{proj}/instances` | ✅ |
| Cloud Run | `/run/v1` | ✅ |
| Cloud Logging | `/logging/v2/entries` | ✅ |
| Cloud Monitoring | `/monitoring/v3/projects/{proj}/timeSeries` | ✅ |
| Secret Manager | `/v1/projects/{proj}/secrets` | ✅ |
| Cloud KMS | `/v1/projects/{proj}/locations/{loc}/keyRings` | ✅ |
| Compute Engine | `/compute/v1/projects/{proj}/zones/{zone}/instances` | ✅ |
| Artifact Registry | `/v1/projects/{proj}/locations/{loc}/repositories` | ✅ |
| Metadata Server | `/computeMetadata/v1/` | ✅ |
| Cloud IAM | `/v1/projects/{proj}/serviceAccounts` | ✅ |

## Admin Endpoints

```bash
curl http://localhost:4566/_gcp/health
curl -X POST http://localhost:4566/_gcp/reset
```
