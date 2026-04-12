# MiniStack — Multi-Cloud Local Emulator Documentation

> **102 services across 4 clouds on a single port** — AWS · Azure · Huawei Cloud · GCP

## Documentation Index

| Document | Description |
|----------|-------------|
| [Getting Started](getting-started.md) | Quick installation, first run, and basic usage |
| [AWS Services](aws.md) | Complete guide to 41 AWS service emulators |
| [Azure Services](azure.md) | Complete guide to 30 Azure service emulators |
| [Huawei Cloud](huawei.md) | Complete guide to 17 Huawei Cloud service emulators |
| [GCP Services](gcp.md) | Complete guide to 14 GCP service emulators |
| [Multi-Cloud Operations](multi-cloud.md) | Running multiple clouds, provider detection, CLOUD_MODE |
| [API Reference](api-reference.md) | All internal endpoints, health checks, reset endpoints |
| [Troubleshooting](troubleshooting.md) | Common issues, debugging, and solutions |

## Quick Reference

### Start / Stop

```bash
# Shell scripts (recommended)
./bin/ministack-start              # All clouds
./bin/ministack-start aws          # AWS only
./bin/ministack-stop               # Stop all

# Make targets
make start-all                     # All clouds
make stop-all                      # Stop all
make run-azure                     # Azure only
make stop-azure                    # Stop Azure only
```

### Health Checks

```bash
curl http://localhost:4566/_ministack/health    # AWS
curl http://localhost:4566/_azure/health         # Azure
curl http://localhost:4566/_huawei/health        # Huawei Cloud
curl http://localhost:4566/_gcp/health           # GCP
curl http://localhost:4566/_multicloud/health    # All clouds
```

### Cloud Mode

| `CLOUD_MODE` | Behavior |
|---|---|
| `all` (default) | All 4 clouds active — auto-detected per request |
| `aws` | AWS only |
| `azure` | Azure only |
| `huawei` | Huawei Cloud only |
| `gcp` | GCP only |

### Service Counts

| Cloud | Services | Key Examples |
|-------|----------|-------------|
| AWS | 41 | S3, SQS, DynamoDB, Lambda, RDS, EC2 |
| Azure | 30 | Blob Storage, Entra ID, Service Bus, Cosmos DB |
| Huawei Cloud | 17 | OBS, SMN, FunctionGraph, RDS, DCS |
| GCP | 14 | GCS, Pub/Sub, Cloud Functions, BigQuery |
| **Total** | **102** | |
