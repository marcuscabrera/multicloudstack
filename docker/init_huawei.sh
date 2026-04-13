#!/bin/bash
# Huawei Cloud initialization script for MiniStack test environment
# Creates initial OBS buckets, SMN topics, and other Huawei resources

set -e

echo "=== Initializing Huawei Cloud resources for tests ==="

# Wait for MiniStack to be ready
echo "Waiting for MiniStack to start..."
sleep 5

PROJECT_ID="0000000000000000"
REGION="cn-north-4"

# Create OBS bucket
curl -s -X PUT "http://localhost:4566/v1/test-obs-bucket" \
    -H "Content-Type: application/json" \
    -H "X-Sdk-Date: 20240101T000000Z" \
    -H "X-Auth-Token: test-token" 2>/dev/null || true

curl -s -X PUT "http://localhost:4566/v1/ministack-huawei-data" \
    -H "Content-Type: application/json" \
    -H "X-Sdk-Date: 20240101T000000Z" \
    -H "X-Auth-Token: test-token" 2>/dev/null || true

# Create SMN topic
curl -s -X POST "http://localhost:4566/v2/${PROJECT_ID}/notifications/topics" \
    -H "Content-Type: application/json" \
    -H "X-Sdk-Date: 20240101T000000Z" \
    -H "X-Auth-Token: test-token" \
    -d '{"name": "test-topic"}' 2>/dev/null || true

# Create FunctionGraph function
curl -s -X POST "http://localhost:4566/v2/${PROJECT_ID}/fgs/functions" \
    -H "Content-Type: application/json" \
    -H "X-Sdk-Date: 20240101T000000Z" \
    -H "X-Auth-Token: test-token" \
    -d '{"func_name": "init-function", "runtime": "Python3.9", "handler": "index.handler"}' 2>/dev/null || true

# Create VPC
curl -s -X POST "http://localhost:4566/v1/${PROJECT_ID}/vpcs" \
    -H "Content-Type: application/json" \
    -H "X-Sdk-Date: 20240101T000000Z" \
    -H "X-Auth-Token: test-token" \
    -d '{"vpc": {"name": "test-vpc", "cidr": "192.168.0.0/16"}}' 2>/dev/null || true

echo "=== Huawei Cloud initialization complete ==="
