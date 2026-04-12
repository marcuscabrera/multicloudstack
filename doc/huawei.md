# Huawei Cloud Services

## Overview

MiniStack emulates **17 Huawei Cloud services** on port `4566`. Services are detected via `x-auth-token`, `x-sdk-date`, `SDK-HMAC-SHA256` headers, or `/v1.0/`, `/v2/`, `/v3/` path prefixes.

## Quick Start

```bash
./bin/ministack-start huawei

# Verify
curl http://localhost:4566/_huawei/health
```

## IAM / Authentication

### Obtain Token

```bash
curl -X POST "http://localhost:4566/v3/auth/tokens" \
  -d '{"auth": {"methods": ["token"], "scope": {"project": {"id": "0000000000000000"}}}}' \
  -H "Content-Type: application/json"
```

Response header `X-Subject-Token` contains the token.

### OIDC Discovery

```bash
curl http://localhost:4566/tenant/00000000-0000-0000-0000-000000000000/.well-known/openid-configuration
```

## OBS (Object Storage Service)

OBS is S3-compatible, reusing the S3 handler with Huawei-specific headers.

### Create Bucket

```bash
curl -X PUT "http://localhost:4566/v1/my-bucket" \
  -H "X-Auth-Token: test-token"
```

### Upload Object

```bash
curl -X PUT "http://localhost:4566/v1/my-bucket/hello.txt" \
  -d "Hello Huawei!" \
  -H "X-Auth-Token: test-token"
```

### List Buckets

```bash
curl "http://localhost:4566/v1/" \
  -H "X-Auth-Token: test-token"
```

## SMN (Simple Message Notification)

### Create Topic

```bash
curl -X POST "http://localhost:4566/v2/0000000000000000/notifications/topics" \
  -d '{"name": "my-topic"}' \
  -H "Content-Type: application/json"
```

### Publish Message

```bash
curl -X POST "http://localhost:4566/v2/0000000000000000/notifications/topics/my-topic/publish" \
  -d '{"message": "Hello SMN"}' \
  -H "Content-Type: application/json"
```

## FunctionGraph

### Create Function

```bash
curl -X POST "http://localhost:4566/v2/0000000000000000/fgs/functions" \
  -d '{"func_name": "hello", "runtime": "Python3.9", "handler": "index.handler"}' \
  -H "Content-Type: application/json"
```

### Invoke Function

```bash
curl -X POST "http://localhost:4566/api/hello" \
  -d '{"name": "Huawei"}' \
  -H "Content-Type: application/json"
```

## RDS

```bash
curl -X POST "http://localhost:4566/v3/0000000000000000/instances" \
  -d '{"name": "my-rds", "datastore": {"type": "MySQL", "version": "8.0"}}' \
  -H "Content-Type: application/json"
```

## DCS (Distributed Cache Service)

```bash
curl -X POST "http://localhost:4566/v2/0000000000000000/instances" \
  -d '{"name": "my-redis", "engine": "Redis", "engine_version": "6.0"}' \
  -H "Content-Type: application/json"
```

## LTS (Log Tank Service)

### Create Log Group

```bash
curl -X POST "http://localhost:4566/v2/0000000000000000/groups" \
  -d '{"log_group_name": "my-logs", "ttl_in_days": 7}' \
  -H "Content-Type: application/json"
```

### Push Logs

```bash
curl -X POST "http://localhost:4566/v2/0000000000000000/groups/{group_id}/streams/{stream_id}/logs" \
  -d '{"log_events": [{"content": "Log message", "time": 1700000000000}]}' \
  -H "Content-Type: application/json"
```

## VPC

### Create VPC

```bash
curl -X POST "http://localhost:4566/v1/0000000000000000/vpcs" \
  -d '{"vpc": {"name": "my-vpc", "cidr": "192.168.0.0/16"}}' \
  -H "Content-Type: application/json"
```

## Complete Service List

| Service | API Path | Status |
|---------|----------|--------|
| OBS | `/v1/{bucket}` | ✅ Full (S3-compatible) |
| IAM | `/v3/auth/tokens` | ✅ Token auth |
| SMN | `/v2/{proj}/notifications/topics` | ✅ |
| FunctionGraph | `/v2/{proj}/fgs/functions` | ✅ |
| RDS | `/v3/{proj}/instances` | ✅ |
| DCS | `/v2/{proj}/instances` | ✅ |
| LTS | `/v2/{proj}/groups` | ✅ |
| VPC | `/v1/{proj}/vpcs` | ✅ |
| DMS | `/v1.0/{proj}/queues` | ✅ Stub |
| AOM | `/v1/{proj}/ams/metrics` | ✅ Stub |
| ECS | `/v1/{proj}/cloudservers` | ✅ Stub |
| APIG | `/v2/{proj}/apigw/instances` | ✅ Stub |
| DIS | `/v2/{proj}/streams` | ✅ Stub |
| KMS | `/v1.0/{proj}/kms/keys` | ✅ Stub |
| CSMS | `/v1/{proj}/secrets` | ✅ Stub |
| CCE | `/api/v3/{proj}/clusters` | ✅ Stub |
| RFS | `/v1/{proj}/stacks` | ✅ Stub |

## Admin Endpoints

```bash
curl http://localhost:4566/_huawei/health
curl -X POST http://localhost:4566/_huawei/reset
```
