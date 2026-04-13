"""
Pytest fixtures for MiniStack multi-cloud integration tests.
Shared fixtures for AWS, Azure, GCP, and Huawei Cloud testing.
"""
import os
import time
import json
import urllib.request
from contextlib import contextmanager

import pytest
import docker

# Endpoint configuration
ENDPOINT = os.environ.get("MINISTACK_ENDPOINT", "http://localhost:4566")
REGION_AWS = "us-east-1"
REGION_GCP = "us-central1"
REGION_AZURE = "eastus"
REGION_HUAWEI = "cn-north-4"

# Default credentials/IDs for each cloud
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID", "test")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "test")
GCP_PROJECT = os.environ.get("GCP_PROJECT_ID", "ministack-test")
AZURE_SUBSCRIPTION_ID = os.environ.get("AZURE_SUBSCRIPTION_ID", "00000000-0000-0000-0000-000000000001")
AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID", "00000000-0000-0000-0000-000000000000")
HUAWEI_PROJECT_ID = os.environ.get("HUAWEICLOUD_PROJECT_ID", "0000000000000000")


def _request(method, path, data=None, headers=None, timeout=10):
    """Send HTTP request to MiniStack endpoint."""
    url = f"{ENDPOINT}{path}"
    req_headers = {**(headers or {})}
    if data is not None:
        if isinstance(data, (dict, list)):
            req_headers["Content-Type"] = "application/json"
            body = json.dumps(data).encode()
        elif isinstance(data, bytes):
            body = data
        else:
            body = str(data).encode()
    else:
        body = None
    
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp_data = resp.read()
            return resp.status, json.loads(resp_data) if resp_data else {}, dict(resp.headers)
    except urllib.error.HTTPError as e:
        resp_data = e.read()
        return e.code, json.loads(resp_data) if resp_data else {}, {}


@pytest.fixture(scope="session")
def docker_client():
    """Create Docker client for container management."""
    return docker.from_env()


@pytest.fixture(scope="session")
def ministack_container(docker_client):
    """
    Spin up MiniStack container with all 4 clouds enabled.
    Skipped if running against existing endpoint.
    """
    # Check if endpoint is already available (external MiniStack)
    try:
        _request("GET", "/_ministack/health")
        yield None  # External instance, don't manage container
        return
    except Exception:
        pass  # No external instance, start container
    
    container = None
    try:
        container = docker_client.containers.run(
            "ministackorg/ministack:latest",
            ports={"4566/tcp": 4566},
            environment={
                "CLOUD_MODE": "all",
                "PERSIST_STATE": "0",
                "LOG_LEVEL": "WARNING",
                "GCP_PROJECT_ID": GCP_PROJECT,
                "AZURE_SUBSCRIPTION_ID": AZURE_SUBSCRIPTION_ID,
                "HUAWEICLOUD_PROJECT_ID": HUAWEI_PROJECT_ID,
            },
            detach=True,
            remove=True,
            healthcheck={
                "test": ["CMD", "python", "-c", f"import urllib.request; urllib.request.urlopen('{ENDPOINT}/_ministack/health')"],
                "interval": 5000000000,  # 5s in nanoseconds
                "timeout": 3000000000,
                "retries": 3,
            }
        )
        
        # Wait for ready (health check)
        for _ in range(60):
            try:
                status, _, _ = _request("GET", "/_ministack/health")
                if status == 200:
                    break
            except Exception:
                time.sleep(0.5)
        else:
            pytest.fail("MiniStack não iniciou em 30s")
        
        yield container
    finally:
        if container:
            container.stop()
            container.remove(force=True)


@pytest.fixture(autouse=True)
def reset_all():
    """Reset all cloud state between tests for isolation."""
    yield
    try:
        _request("POST", "/_multicloud/reset")
    except Exception:
        pass  # Reset may not be available in all modes


# ── AWS Fixtures ────────────────────────────────────────────

@pytest.fixture
def aws_credentials():
    """Return AWS credentials for boto3 clients."""
    return {
        "endpoint_url": ENDPOINT,
        "aws_access_key_id": AWS_ACCESS_KEY,
        "aws_secret_access_key": AWS_SECRET_KEY,
        "region_name": REGION_AWS,
    }


@pytest.fixture
def s3_client(aws_credentials):
    """Create S3 boto3 client."""
    import boto3
    return boto3.client("s3", **aws_credentials)


@pytest.fixture
def lambda_client(aws_credentials):
    """Create Lambda boto3 client."""
    import boto3
    return boto3.client("lambda", **aws_credentials)


# ── GCP Fixtures ────────────────────────────────────────────

@pytest.fixture
def gcp_headers():
    """Return GCP-style headers for API requests."""
    return {
        "Content-Type": "application/json",
        "x-goog-api-client": "ministack-test/1.0",
        "Authorization": f"Bearer ya29.test-token",
    }


@pytest.fixture
def gcp_project():
    """Return GCP project ID."""
    return GCP_PROJECT


# ── Azure Fixtures ──────────────────────────────────────────

@pytest.fixture
def azure_headers():
    """Return Azure-style headers for API requests."""
    import time
    return {
        "Content-Type": "application/json",
        "x-ms-date": time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()),
        "x-ms-version": "2023-11-03",
        "Authorization": "Bearer test-token",
    }


@pytest.fixture
def azure_subscription_id():
    """Return Azure subscription ID."""
    return AZURE_SUBSCRIPTION_ID


# ── Huawei Fixtures ─────────────────────────────────────────

@pytest.fixture
def huawei_headers():
    """Return Huawei-style headers for API requests."""
    return {
        "Content-Type": "application/json",
        "X-Sdk-Date": "20240101T000000Z",
        "X-Auth-Token": "test-token",
    }


@pytest.fixture
def huawei_project_id():
    """Return Huawei project ID."""
    return HUAWEI_PROJECT_ID


# ── Utility Fixtures ────────────────────────────────────────

@pytest.fixture
def http_request():
    """Return the _request function for custom HTTP calls."""
    return _request


@pytest.fixture
def unique_suffix():
    """Generate unique suffix for resource names to avoid conflicts."""
    import uuid
    return str(uuid.uuid4())[:8]
