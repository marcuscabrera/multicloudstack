# MiniStack for Google Cloud Platform (GCP)

Local emulator for **GCP services**, built on the MiniStack architecture.
Emulates 14 GCP services on a single port (`4566`), compatible with the official
`google-cloud-*` Python SDKs and Terraform `google` provider.

## Quick Start

### Docker (GCP Mode Only)

```bash
docker compose -f docker-compose.gcp.yml up -d --build
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CLOUD_MODE` | `all` | `all` = all clouds, `gcp` = GCP only |
| `GCP_PROJECT_ID` | `ministack-emulator` | Default project ID |
| `GCP_REGION` | `us-central1` | Default region |
| `GCP_ZONE` | `us-central1-a` | Default zone |

## Supported Services

| Service | API Path | Status |
|---------|----------|--------|
| **Cloud Storage (GCS)** | `/storage/v1/b` | ✅ Bucket/object CRUD |
| **Pub/Sub** | `/v1/projects/{proj}/topics` | ✅ Topics, subscriptions, publish/pull |
| **Cloud Functions** | `/v1/projects/{proj}/locations/{loc}/functions` | ✅ CRUD, HTTP invoke |
| **BigQuery** | `/bigquery/v2/projects/{proj}` | ✅ Datasets, jobs, queries |
| **Cloud SQL** | `/sql/v1beta4/projects/{proj}/instances` | ✅ Instance CRUD |
| **Cloud Run** | `/run/v1` | ✅ Service CRUD |
| **Cloud Logging** | `/logging/v2/entries` | ✅ Write/read log entries |
| **Cloud Monitoring** | `/monitoring/v3/projects/{proj}/timeSeries` | ✅ Metric publish/query |
| **Secret Manager** | `/v1/projects/{proj}/secrets` | ✅ Secret CRUD, versions, access |
| **Cloud KMS** | `/v1/projects/{proj}/locations/{loc}/keyRings` | ✅ Key rings, keys, encrypt/decrypt |
| **Compute Engine** | `/compute/v1/projects/{proj}/zones/{zone}/instances` | ✅ VM CRUD |
| **Artifact Registry** | `/v1/projects/{proj}/locations/{loc}/repositories` | ✅ Repository CRUD |
| **Metadata Server** | `/computeMetadata/v1/` | ✅ Project, SA, token, zone |
| **Cloud IAM** | `/v1/projects/{proj}/serviceAccounts` | ✅ Service account CRUD |

## Admin Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/_gcp/health` | GET | GCP service health check |
| `/_gcp/reset` | POST | Reset all GCP service state |

## Usage Examples

### Python SDK

```python
from google.cloud import storage, pubsub_v1

# GCS (no credentials needed — emulated)
client = storage.Client(project="ministack-emulator",
                        client_options={"api_endpoint": "http://localhost:4566"})
bucket = client.create_bucket("my-bucket")
blob = bucket.blob("hello.txt")
blob.upload_from_string("Hello MiniStack!")

# Pub/Sub
publisher = pubsub_v1.PublisherClient(client_options={"api_endpoint": "http://localhost:4566"})
topic = publisher.create_topic(name="projects/ministack-emulator/topics/my-topic")
publisher.publish(topic, b"Hello Pub/Sub!")

subscriber = pubsub_v1.SubscriberClient(client_options={"api_endpoint": "http://localhost:4566"})
subscription = subscriber.create_subscription(
    name="projects/ministack-emulator/subscriptions/my-sub",
    topic="projects/ministack-emulator/topics/my-topic"
)
```

### Raw HTTP

```python
import requests

BASE = "http://localhost:4566"
PROJECT = "ministack-emulator"

# Create bucket
resp = requests.post(f"{BASE}/storage/v1/b", json={"name": "my-bucket"})
print(resp.json())

# List buckets
resp = requests.get(f"{BASE}/storage/v1/b")
print(resp.json())

# Create Pub/Sub topic
resp = requests.put(f"{BASE}/v1/projects/{PROJECT}/topics/my-topic")
print(resp.json())

# Publish message
resp = requests.post(f"{BASE}/v1/projects/{PROJECT}/topics/my-topic:publish",
                     json={"messages": [{"data": "SGVsbG8="}]})
print(resp.json())

# Metadata server
resp = requests.get(f"{BASE}/computeMetadata/v1/project/project-id")
print(resp.text)  # ministack-emulator
```

### Terraform google provider

```hcl
provider "google" {
  project = "ministack-emulator"
  region  = "us-central1"

  # Override endpoint via environment variables or custom endpoints
  # GOOGLE_STORAGE_CUSTOM_ENDPOINT = "http://localhost:4566"
  # GOOGLE_PUBSUB_CUSTOM_ENDPOINT = "http://localhost:4566"
}

resource "google_storage_bucket" "dev" {
  name = "dev-bucket"
}
```

## Metadata Server

The GCP metadata server is emulated at `/computeMetadata/v1/`:

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

## Operation Modes

| `CLOUD_MODE` | Behavior |
|---|---|
| `all` (default) | All clouds active — GCP detected by `x-goog-*` headers or `/storage/`, `/pubsub/`, etc. |
| `gcp` | GCP only |
| `aws` / `azure` / `huawei` | Other clouds only |

## Running Tests

```bash
export CLOUD_MODE=gcp
python -m uvicorn ministack.app:app --host 0.0.0.0 --port 4566 &
pytest tests/test_gcp_services.py -v
```

## Differences from Real GCP

- All services are **in-memory** emulators (no persistent infrastructure)
- Authentication uses **stub tokens** — no real IAM validation
- No **billing, quotas, rate limiting, or IAM policies**
- No **real networking** (all endpoints are localhost)
- Cloud Functions invoke uses the same Lambda warm worker pool

## License

MIT — same as MiniStack upstream.
