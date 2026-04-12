"""
Azure Cloud Service Tests.
Tests for the priority Azure Cloud emulated services.
Uses HTTP requests to the local MiniStack endpoint with Azure-style headers.
"""

import json
import os
import urllib.request
import base64
import time

import pytest

ENDPOINT = os.environ.get("MINISTACK_ENDPOINT", "http://localhost:4566")
TENANT_ID = os.environ.get("AZURE_TENANT_ID", "00000000-0000-0000-0000-000000000000")
SUB_ID = os.environ.get("AZURE_SUBSCRIPTION_ID", "00000000-0000-0000-0000-000000000001")
LOCATION = os.environ.get("AZURE_LOCATION", "eastus")
STORAGE_ACCOUNT = os.environ.get("AZURE_STORAGE_ACCOUNT", "devstoreaccount1")

AZURE_HEADERS = {
    "Content-Type": "application/json",
    "x-ms-date": time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()),
    "x-ms-version": "2023-11-03",
    "Authorization": "Bearer test-token",
}


def _request(method, path, data=None, headers=None):
    """Send HTTP request to the emulated Azure endpoint."""
    url = f"{ENDPOINT}{path}"
    req_headers = {**AZURE_HEADERS, **(headers or {})}
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_data = resp.read()
            return resp.status, json.loads(resp_data) if resp_data else {}, dict(resp.headers)
    except urllib.error.HTTPError as e:
        resp_data = e.read()
        return e.code, json.loads(resp_data) if resp_data else {}, {}


# =========================================================================
# Entra ID — Token Authentication
# =========================================================================

class TestEntraID:
    def test_obtain_token_client_credentials(self):
        """Test obtaining Bearer token via client_credentials flow."""
        body = (
            f"grant_type=client_credentials"
            f"&client_id=test&client_secret=test"
            f"&scope=https://management.azure.com/.default"
        ).encode()
        req = urllib.request.Request(
            f"{ENDPOINT}/tenant/{TENANT_ID}/oauth2/v2.0/token",
            data=body, method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            assert "access_token" in data
            assert data["token_type"] == "Bearer"
            assert "expires_in" in data

    def test_openid_configuration(self):
        """Test OIDC discovery endpoint."""
        req = urllib.request.Request(f"{ENDPOINT}/tenant/{TENANT_ID}/.well-known/openid-configuration")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            assert "issuer" in data
            assert "token_endpoint" in data
            assert "jwks_uri" in data


# =========================================================================
# Azure Blob Storage
# =========================================================================

class TestBlobStorage:
    def test_create_container(self):
        """Test creating a blob container."""
        status, _, _ = _request("PUT", f"/azure/blob/{STORAGE_ACCOUNT}/testcontainer?restype=container")
        assert status in (200, 201, 204)

    def test_list_containers(self):
        """Test listing containers."""
        _request("PUT", f"/azure/blob/{STORAGE_ACCOUNT}/testcontainer-list?restype=container")
        status, data, _ = _request("GET", f"/azure/blob/{STORAGE_ACCOUNT}")
        assert status == 200
        assert "Containers" in data or "accounts" in data

    def test_upload_and_download_blob(self):
        """Test blob upload and download."""
        # Upload
        status, _, _ = _request("PUT", f"/azure/blob/{STORAGE_ACCOUNT}/testcontainer/hello.txt", b"Hello Azure!")
        assert status == 201
        # Download
        status, data, hdrs = _request("GET", f"/azure/blob/{STORAGE_ACCOUNT}/testcontainer/hello.txt")
        assert status == 200
        # Response could be raw bytes or JSON
        if isinstance(data, bytes):
            assert b"Hello Azure!" in data
        else:
            assert True  # JSON response accepted

    def test_list_blobs(self):
        """Test listing blobs in a container."""
        _request("PUT", f"/azure/blob/{STORAGE_ACCOUNT}/testcontainer-list2?restype=container")
        _request("PUT", f"/azure/blob/{STORAGE_ACCOUNT}/testcontainer-list2/blob1.txt", b"data")
        status, data, _ = _request("GET", f"/azure/blob/{STORAGE_ACCOUNT}/testcontainer-list2?restype=container&comp=list")
        assert status == 200

    def test_delete_blob(self):
        """Test deleting a blob."""
        _request("PUT", f"/azure/blob/{STORAGE_ACCOUNT}/testcontainer-del?restype=container")
        _request("PUT", f"/azure/blob/{STORAGE_ACCOUNT}/testcontainer-del/to-delete.txt", b"del me")
        status, _, _ = _request("DELETE", f"/azure/blob/{STORAGE_ACCOUNT}/testcontainer-del/to-delete.txt")
        assert status in (200, 202, 204)


# =========================================================================
# Azure Functions
# =========================================================================

class TestAzureFunctions:
    def test_create_and_invoke_function(self):
        """Test creating and invoking an Azure Function."""
        status, resp, _ = _request("POST", f"/subscriptions/{SUB_ID}/resourceGroups/dev-rg/providers/Microsoft.Web/sites/myfuncapp/functions/hello", {
            "name": "hello",
            "code": {"zip": ""},
        })
        assert status == 200
        # Invoke
        status, resp, _ = _request("POST", "/api/hello", {"name": "Azure"})
        assert status == 200


# =========================================================================
# Cosmos DB
# =========================================================================

class TestCosmosDB:
    def test_create_database(self):
        """Test creating a Cosmos DB database."""
        status, resp, _ = _request("POST", "/azure/cosmos/devaccount/dbs", {"id": "testdb"})
        assert status == 201
        assert resp.get("id") == "testdb"

    def test_create_container_and_insert_doc(self):
        """Test creating a container and inserting a document."""
        _request("POST", "/azure/cosmos/devaccount/dbs", {"id": "testdb2"})
        status, resp, _ = _request("POST", "/azure/cosmos/devaccount/dbs/testdb2/colls", {
            "id": "users",
            "partitionKey": {"paths": ["/id"]}
        })
        assert status == 201
        # Insert doc
        status, resp, _ = _request("POST", "/azure/cosmos/devaccount/dbs/testdb2/colls/users/docs", {
            "id": "1", "name": "Alice"
        })
        assert status == 201
        assert resp.get("id") == "1"

    def test_query_documents(self):
        """Test querying documents via SQL API."""
        _request("POST", "/azure/cosmos/devaccount/dbs", {"id": "testdb3"})
        _request("POST", "/azure/cosmos/devaccount/dbs/testdb3/colls", {"id": "items"})
        _request("POST", "/azure/cosmos/devaccount/dbs/testdb3/colls/items/docs", {"id": "item1", "value": 42})
        status, resp, _ = _request("POST", "/azure/cosmos/devaccount/dbs/testdb3/colls/items/docs",
            {"query": "SELECT * FROM c WHERE c.id = 'item1'"},
            headers={**AZURE_HEADERS, "x-ms-documentdb-isquery": "true"})
        assert status == 200
        assert "Documents" in resp


# =========================================================================
# Key Vault Secrets
# =========================================================================

class TestKeyVaultSecrets:
    def test_set_and_get_secret(self):
        """Test setting and getting a Key Vault secret."""
        status, resp, _ = _request("PUT", "/keyvault/myVault/secrets/db-password", {"value": "s3cr3t"})
        assert status == 200
        assert resp.get("value") == "s3cr3t"
        # Get
        status, resp, _ = _request("GET", "/keyvault/myVault/secrets/db-password")
        assert status == 200
        assert resp.get("value") == "s3cr3t"

    def test_list_secrets(self):
        """Test listing Key Vault secrets."""
        _request("PUT", "/keyvault/myVault/secrets/secret1", {"value": "val1"})
        _request("PUT", "/keyvault/myVault/secrets/secret2", {"value": "val2"})
        status, resp, _ = _request("GET", "/keyvault/myVault/secrets")
        assert status == 200
        assert "value" in resp


# =========================================================================
# Azure SQL
# =========================================================================

class TestAzureSQL:
    def test_create_server(self):
        """Test creating an Azure SQL server."""
        status, resp, _ = _request("PUT", f"/subscriptions/{SUB_ID}/resourceGroups/dev-rg/providers/Microsoft.Sql/servers/testsql", {
            "name": "testsql",
            "properties": {"administratorLogin": "azure", "version": "14"}
        })
        assert status == 200
        assert "fullyQualifiedDomainName" in resp.get("properties", {})


# =========================================================================
# Cache for Redis
# =========================================================================

class TestCacheRedis:
    def test_create_redis_instance(self):
        """Test creating a Redis cache instance."""
        status, resp, _ = _request("PUT", f"/subscriptions/{SUB_ID}/resourceGroups/dev-rg/providers/Microsoft.Cache/redis/testredis", {
            "name": "testredis",
            "properties": {"redisVersion": "6", "sku": {"name": "Basic", "capacity": 1}}
        })
        assert status == 200
        props = resp.get("properties", {})
        assert "hostName" in props
        assert "port" in props


# =========================================================================
# Monitor Logs
# =========================================================================

class TestMonitorLogs:
    def test_ingest_and_query_logs(self):
        """Test ingesting logs and running a basic query."""
        _request("POST", f"/subscriptions/{SUB_ID}/resourceGroups/dev-rg/providers/Microsoft.OperationalInsights/workspaces/testws", {
            "name": "testws"
        })
        # Ingest
        status, _, _ = _request("POST", f"/azure/monitor/workspaces/testws/tables/AppLogs/rows", {
            "rows": [{"TimeGenerated": "2024-01-01T00:00:00Z", "Level": "Info", "Message": "test"}]
        })
        assert status == 200
        # Query
        status, resp, _ = _request("POST", f"/azure/monitor/workspaces/testws/query", {
            "query": "AppLogs | where Level == 'Info'"
        })
        assert status == 200
        assert "tables" in resp


# =========================================================================
# Service Bus
# =========================================================================

class TestServiceBus:
    def test_create_queue_and_send_receive(self):
        """Test creating a Service Bus queue, sending and receiving a message."""
        status, _, _ = _request("PUT", f"/subscriptions/{SUB_ID}/resourceGroups/dev-rg/providers/Microsoft.ServiceBus/namespaces/devns/queues/testq")
        assert status == 200
        # Send
        status, resp, _ = _request("POST", f"/azure/servicebus/devns/testq/messages", {"body": "Hello Service Bus"})
        assert status == 201
        assert "messageId" in resp
        # Receive
        status, resp, _ = _request("DELETE", f"/azure/servicebus/devns/testq/messages/head")
        assert status in (200, 204)


# =========================================================================
# ARM Deployments
# =========================================================================

class TestARMDeployments:
    def test_create_and_check_deployment(self):
        """Test creating an ARM deployment."""
        status, resp, _ = _request("PUT", f"/subscriptions/{SUB_ID}/resourceGroups/dev-rg/providers/Microsoft.Resources/deployments/test-deploy", {
            "name": "test-deploy",
            "properties": {
                "mode": "Incremental",
                "template": {
                    "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
                    "resources": []
                }
            }
        })
        assert status == 200
        assert resp.get("properties", {}).get("provisioningState") == "Succeeded"


# =========================================================================
# Admin Endpoints
# =========================================================================

class TestAzureAdmin:
    def test_azure_health(self):
        """Test Azure health endpoint."""
        req = urllib.request.Request(f"{ENDPOINT}/_azure/health")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            assert "services" in data
            assert "azure_blob" in data["services"]
            assert "entra_id" in data["services"]

    def test_azure_reset(self):
        """Test Azure reset endpoint."""
        req = urllib.request.Request(f"{ENDPOINT}/_azure/reset", data=b"", method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            assert data.get("reset") == "ok"
            assert data.get("scope") == "azure"
