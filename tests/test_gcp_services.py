"""
GCP Cloud Service Tests.
Tests for the priority GCP emulated services.
"""

import json
import os
import urllib.request
import time

import pytest

ENDPOINT = os.environ.get("MINISTACK_ENDPOINT", "http://localhost:4566")
PROJECT = os.environ.get("GCP_PROJECT_ID", "ministack-emulator")
REGION = os.environ.get("GCP_REGION", "us-central1")

GCP_HEADERS = {
    "Content-Type": "application/json",
    "x-goog-api-client": "ministack-test/1.0",
}


def _request(method, path, data=None, headers=None):
    url = f"{ENDPOINT}{path}"
    req_headers = {**GCP_HEADERS, **(headers or {})}
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_data = resp.read()
            return resp.status, json.loads(resp_data) if resp_data else {}
    except urllib.error.HTTPError as e:
        resp_data = e.read()
        return e.code, json.loads(resp_data) if resp_data else {}


# =========================================================================
# GCS (Cloud Storage)
# =========================================================================

class TestGCS:
    def test_create_bucket(self):
        status, resp = _request("POST", "/storage/v1/b", {"name": "test-bucket-gcs"})
        assert status == 200
        assert resp.get("name") == "test-bucket-gcs"

    def test_list_buckets(self):
        _request("POST", "/storage/v1/b", {"name": "test-bucket-list"})
        status, resp = _request("GET", "/storage/v1/b")
        assert status == 200
        assert "items" in resp

    def test_create_and_list_object(self):
        _request("POST", "/storage/v1/b", {"name": "test-obj-bucket"})
        status, resp = _request("POST", "/storage/v1/b/test-obj-bucket/o", {"name": "hello.txt"})
        assert status == 200
        assert resp.get("name") == "hello.txt"


# =========================================================================
# Pub/Sub
# =========================================================================

class TestPubSub:
    def test_create_topic_and_publish(self):
        status, resp = _request("PUT", f"/v1/projects/{PROJECT}/topics/test-topic-pub")
        assert status == 200
        # Publish
        status, resp = _request("POST", f"/v1/projects/{PROJECT}/topics/test-topic-pub:publish", {
            "messages": [{"data": "SGVsbG8="}]
        })
        assert status == 200
        assert "messageIds" in resp

    def test_create_subscription_and_pull(self):
        _request("PUT", f"/v1/projects/{PROJECT}/topics/test-topic-pull")
        _request("POST", f"/v1/projects/{PROJECT}/topics/test-topic-pull:publish", {"messages": [{"data": "dGVzdA=="}]})
        status, resp = _request("PUT", f"/v1/projects/{PROJECT}/subscriptions/test-sub-pull", {
            "topic": f"projects/{PROJECT}/topics/test-topic-pull"
        })
        assert status == 200
        # Pull
        status, resp = _request("POST", f"/v1/projects/{PROJECT}/subscriptions/test-sub-pull:pull", {})
        assert status == 200
        assert "receivedMessages" in resp


# =========================================================================
# Cloud Functions
# =========================================================================

class TestCloudFunctions:
    def test_create_and_invoke_function(self):
        status, resp = _request("POST", f"/v1/projects/{PROJECT}/locations/{REGION}/functions/test-fn", {
            "entryPoint": "handler", "runtime": "python311"
        })
        assert status == 200
        # Invoke
        status, resp = _request("POST", f"/gcp/fn/test-fn", {"name": "GCP"})
        assert status == 200


# =========================================================================
# BigQuery
# =========================================================================

class TestBigQuery:
    def test_create_dataset_and_query(self):
        status, resp = _request("POST", f"/bigquery/v2/projects/{PROJECT}/datasets", {
            "datasetReference": {"projectId": PROJECT, "datasetId": "test_ds"}
        })
        assert status == 200
        # Query
        status, resp = _request("POST", f"/bigquery/v2/projects/{PROJECT}/queries", {
            "query": "SELECT 1 as num"
        })
        assert status == 200
        assert "query" in resp


# =========================================================================
# Cloud SQL
# =========================================================================

class TestCloudSQL:
    def test_create_instance(self):
        status, resp = _request("POST", f"/sql/v1beta4/projects/{PROJECT}/instances", {
            "name": "test-sql", "databaseVersion": "POSTGRES_14"
        })
        assert status == 200
        assert resp.get("state") == "RUNNABLE"
        assert "ipAddresses" in resp


# =========================================================================
# Secret Manager
# =========================================================================

class TestSecretManager:
    def test_create_secret_and_access(self):
        status, resp = _request("POST", f"/v1/projects/{PROJECT}/secrets:test-secret")
        assert status == 200
        assert "name" in resp
        # Access
        status, resp = _request("GET", f"/v1/projects/{PROJECT}/secrets/test-secret/versions/latest:access")
        assert status == 200
        assert "payload" in resp


# =========================================================================
# Cloud KMS
# =========================================================================

class TestCloudKMS:
    def test_create_keyring_and_key(self):
        status, resp = _request("POST", f"/v1/projects/{PROJECT}/locations/{REGION}/keyRings:test-kr")
        assert status == 200
        assert "name" in resp
        # Create key
        status, resp = _request("POST", f"/v1/projects/{PROJECT}/locations/{REGION}/keyRings/test-kr/cryptoKeys", {
            "name": "test-key"
        })
        assert status == 200
        assert resp.get("purpose") == "ENCRYPT_DECRYPT"


# =========================================================================
# Metadata Server
# =========================================================================

class TestMetadataServer:
    def test_project_id(self):
        req = urllib.request.Request(f"{ENDPOINT}/computeMetadata/v1/project/project-id")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode()
            assert data == PROJECT

    def test_service_account_token(self):
        req = urllib.request.Request(f"{ENDPOINT}/computeMetadata/v1/instance/service-accounts/default/token")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            assert "access_token" in data
            assert "expires_in" in data


# =========================================================================
# Admin Endpoints
# =========================================================================

class TestGCPAdmin:
    def test_gcp_health(self):
        req = urllib.request.Request(f"{ENDPOINT}/_gcp/health")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            assert "services" in data
            assert "gcp_storage" in data["services"]

    def test_gcp_reset(self):
        req = urllib.request.Request(f"{ENDPOINT}/_gcp/reset", data=b"", method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            assert data.get("reset") == "ok"
            assert data.get("scope") == "gcp"
