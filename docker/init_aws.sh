#!/bin/bash
# AWS initialization script for MiniStack test environment
# Creates initial S3 buckets, SQS queues, and other AWS resources

set -e

echo "=== Initializing AWS resources for tests ==="

# Wait for MiniStack to be ready
echo "Waiting for MiniStack to start..."
sleep 5

# Create test S3 buckets
awslocal s3 mb s3://test-bucket-aws 2>/dev/null || true
awslocal s3 mb s3://ministack-test-data 2>/dev/null || true

# Create test SQS queue
awslocal sqs create-queue --queue-name test-queue-default 2>/dev/null || true

# Create test DynamoDB table
awslocal dynamodb create-table \
    --table-name test-table \
    --attribute-definitions AttributeName=id,AttributeType=S \
    --key-schema AttributeName=id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST 2>/dev/null || true

echo "=== AWS initialization complete ==="
