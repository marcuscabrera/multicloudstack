FROM python:3.12-alpine

LABEL maintainer="MiniStack" \
      description="Local AWS Service Emulator — drop-in LocalStack replacement"

# Upgrade base packages to pick up latest security patches.
RUN apk upgrade --no-cache && apk add --no-cache nodejs && rm -f /usr/bin/wget /bin/wget

WORKDIR /opt/ministack

# Install all Python dependencies.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        uvicorn==0.30.6 \
        "cbor2>=5.4.0" \
        "defusedxml>=0.7" \
        "docker>=7.0.0" \
        "pyyaml>=6.0" \
        "cryptography>=41.0"

COPY ministack/ ministack/

RUN addgroup -S ministack && adduser -S ministack -G ministack
RUN mkdir -p /tmp/ministack-data/s3 && chown -R ministack:ministack /tmp/ministack-data
RUN mkdir -p /docker-entrypoint-initaws.d && chown ministack:ministack /docker-entrypoint-initaws.d
VOLUME /docker-entrypoint-initaws.d

ENV GATEWAY_PORT=4566 \
    LOG_LEVEL=INFO \
    S3_PERSIST=0 \
    S3_DATA_DIR=/tmp/ministack-data/s3 \
    REDIS_HOST=redis \
    REDIS_PORT=6379 \
    RDS_BASE_PORT=15432 \
    RDS_PERSIST=0 \
    ELASTICACHE_BASE_PORT=16379 \
    LAMBDA_EXECUTOR=local \
    PYTHONUNBUFFERED=1 \
    CLOUD_MODE=all \
    HUAWEI_MODE=0 \
    AZURE_MODE=0 \
    HUAWEICLOUD_SDK_AK=test \
    HUAWEICLOUD_SDK_SK=test \
    HUAWEICLOUD_PROJECT_ID=0000000000000000 \
    HUAWEICLOUD_REGION=cn-north-4 \
    AZURE_TENANT_ID=00000000-0000-0000-0000-000000000000 \
    AZURE_SUBSCRIPTION_ID=00000000-0000-0000-0000-000000000001 \
    AZURE_LOCATION=eastus \
    AZURE_CLIENT_ID=test \
    AZURE_CLIENT_SECRET=test \
    AZURE_STORAGE_ACCOUNT=devstoreaccount1 \
    CLOUD_MODE=all \
    GCP_PROJECT_ID=ministack-emulator \
    GCP_REGION=us-central1 \
    GCP_ZONE=us-central1-a

EXPOSE 4566

# Pure Python healthcheck — no curl dependency
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:4566/_ministack/health')" || exit 1

ENTRYPOINT ["python", "-m", "uvicorn", "ministack.app:app", "--host", "0.0.0.0", "--port", "4566"]
