#!/bin/bash
# Azure initialization script for MiniStack test environment
# Creates initial storage accounts, resource groups, and other Azure resources

set -e

echo "=== Initializing Azure resources for tests ==="

# Wait for MiniStack to be ready
echo "Waiting for MiniStack to start..."
sleep 5

SUBSCRIPTION_ID="00000000-0000-0000-0000-000000000001"
RESOURCE_GROUP="dev-rg"

# Create resource group via ARM API
curl -s -X PUT "http://localhost:4566/subscriptions/${SUBSCRIPTION_ID}/resourcegroups/${RESOURCE_GROUP}" \
    -H "Content-Type: application/json" \
    -d '{"location": "eastus"}' 2>/dev/null || true

# Create storage account
curl -s -X PUT "http://localhost:4566/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Storage/storageAccounts/devstoreaccount1" \
    -H "Content-Type: application/json" \
    -d '{"location": "eastus", "sku": {"name": "Standard_LRS"}}' 2>/dev/null || true

# Create Service Bus namespace
curl -s -X PUT "http://localhost:4566/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.ServiceBus/namespaces/devns" \
    -H "Content-Type: application/json" \
    -d '{"location": "eastus"}' 2>/dev/null || true

# Create Cosmos DB account
curl -s -X POST "http://localhost:4566/azure/cosmos/devaccount/dbs" \
    -H "Content-Type: application/json" \
    -d '{"id": "init-db"}' 2>/dev/null || true

echo "=== Azure initialization complete ==="
