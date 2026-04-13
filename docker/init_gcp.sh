#!/bin/bash
# GCP initialization script for MiniStack test environment
# Creates initial GCS buckets, Pub/Sub topics, and other GCP resources

set -e

echo "=== Initializing GCP resources for tests ==="

# Wait for MiniStack to be ready
echo "Waiting for MiniStack to start..."
sleep 5

# Create test GCS bucket via HTTP API
curl -s -X POST "http://localhost:4566/storage/v1/b" \
    -H "Content-Type: application/json" \
    -d '{"name": "test-bucket-gcp"}' 2>/dev/null || true

curl -s -X POST "http://localhost:4566/storage/v1/b" \
    -H "Content-Type: application/json" \
    -d '{"name": "ministack-gcp-data"}' 2>/dev/null || true

# Create test Pub/Sub topic
curl -s -X PUT "http://localhost:4566/v1/projects/ministack-test/topics/test-topic" \
    -H "Content-Type: application/json" 2>/dev/null || true

# Create test BigQuery dataset
curl -s -X POST "http://localhost:4566/bigquery/v2/projects/ministack-test/datasets" \
    -H "Content-Type: application/json" \
    -d '{"datasetReference": {"projectId": "ministack-test", "datasetId": "test_dataset"}}' 2>/dev/null || true

echo "=== GCP initialization complete ==="
