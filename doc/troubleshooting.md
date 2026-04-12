# Troubleshooting

## Common Issues

### Docker Not Starting

**Symptom:** `docker compose up` fails with connection refused.

**Solution:**
```bash
# Check Docker is running
docker info

# Start Docker daemon if needed
sudo systemctl start docker  # Linux
open -a Docker              # macOS
```

### Port Already in Use

**Symptom:** `address already in use` error on port 4566.

**Solution:**
```bash
# Find what's using port 4566
lsof -i :4566
# or
netstat -tulpn | grep 4566

# Kill the process or use a different port
export GATEWAY_PORT=4567
docker compose up -d
```

### Health Check Fails

**Symptom:** `/_ministack/health` returns connection refused or timeout.

**Solution:**
```bash
# Check if container is running
docker ps

# Check container logs
docker logs ministack

# Wait a few seconds for startup
sleep 3
curl http://localhost:4566/_ministack/health
```

### AWS SDK Not Connecting

**Symptom:** boto3 or AWS CLI returns connection errors.

**Solution:**
```bash
# Verify endpoint is accessible
curl http://localhost:4566/_ministack/health

# Check endpoint URL is correct
aws --endpoint-url=http://localhost:4566 s3 ls

# Verify credentials
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
```

### Azure SDK Not Connecting

**Symptom:** `azure-storage-blob` returns authentication error.

**Solution:**
```bash
# Use dev account credentials
export AZURE_CLIENT_ID=test
export AZURE_CLIENT_SECRET=test

# Use permissive auth (any Bearer token accepted)
# Verify token endpoint
curl -X POST "http://localhost:4566/tenant/00000000-0000-0000-0000-000000000000/oauth2/v2.0/token" \
  -d "grant_type=client_credentials&client_id=test&client_secret=test" \
  -H "Content-Type: application/x-www-form-urlencoded"
```

### Huawei Cloud SDK Not Connecting

**Symptom:** Huawei SDK returns signature verification error.

**Solution:**
```bash
# Use dev credentials
export HUAWEICLOUD_SDK_AK=test
export HUAWEICLOUD_SDK_SK=test

# Verify IAM token endpoint
curl -X POST "http://localhost:4566/v3/auth/tokens" \
  -d '{"auth": {"methods": ["token"]}}'
```

### GCP SDK Not Connecting

**Symptom:** `google-cloud-storage` returns 404 or auth error.

**Solution:**
```bash
# Use x-goog-api-client header (auto-added by SDK)
# Verify metadata server
curl http://localhost:4566/computeMetadata/v1/project/project-id

# Check project ID matches
export GCP_PROJECT_ID=ministack-emulator
```

### CLOUD_MODE Issues

**Symptom:** Request routed to wrong cloud.

**Solution:**
```bash
# Check current CLOUD_MODE
curl http://localhost:4566/_multicloud/health | python3 -c "import sys,json; print(json.load(sys.stdin)['cloud_mode'])"

# Ensure CLOUD_MODE includes target cloud
# For all clouds: CLOUD_MODE=all (default)
# For specific cloud: export CLOUD_MODE=gcp
```

### Resource Not Found After Reset

**Symptom:** Resources missing after calling reset endpoint.

**Expected:** Reset wipes ALL state for that cloud. Re-create resources.

```bash
# This is normal behavior after reset
curl -X POST http://localhost:4566/_ministack/reset

# Re-create your resources
aws --endpoint-url=http://localhost:4566 s3 mb s3://my-bucket
```

### Lambda Function Not Invoking

**Symptom:** Lambda invoke returns error or hangs.

**Solution:**
```bash
# Check Lambda execution mode
# Default: local (subprocess), can use docker
export LAMBDA_EXECUTOR=local  # or docker

# Check function exists
aws --endpoint-url=http://localhost:4566 lambda get-function --function-name my-fn

# Check runtime is supported (Python, Node.js)
# Verify handler function name matches
```

### Redis Not Available

**Symptom:** ElastiCache/DCS returns error about missing Redis.

**Solution:**
```bash
# Redis is required for some Azure/Huawei services
# Ensure Redis container is running
docker compose up -d redis

# Check Redis is accessible
docker exec ministack-redis redis-cli ping  # Should return PONG
```

## Debugging

### Enable Debug Logging

```bash
export LOG_LEVEL=DEBUG
docker compose down
docker compose up -d
docker compose logs -f
```

### View Logs

```bash
# AWS logs
docker logs -f ministack

# Azure logs
docker compose -f docker-compose.azure.yml logs -f

# Huawei logs
docker compose -f docker-compose.huawei.yml logs -f

# GCP logs
docker compose -f docker-compose.gcp.yml logs -f
```

### Check Container Status

```bash
docker ps -a

# Check specific container
docker inspect ministack | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['State']['Status'])"
```

### Test Network Connectivity

```bash
# From inside container
docker exec ministack curl -s http://localhost:4566/_ministack/health

# From host
curl -v http://localhost:4566/_ministack/health
```

### State Persistence

If `PERSIST_STATE=1`, state is saved on shutdown:

```bash
export PERSIST_STATE=1
export STATE_DIR=/tmp/ministack-state

# State is saved to $STATE_DIR/*.json on container stop
# State is reloaded on container start
```

## Getting Help

- **Issues:** https://github.com/ministackorg/ministack-huawei/issues
- **Documentation:** See other docs in `doc/` directory
- **READMEs:** `README.md`, `README_AZURE.md`, `README_HUAWEI.md`, `README_GCP.md`
