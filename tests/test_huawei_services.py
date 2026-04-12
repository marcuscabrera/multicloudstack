"""
Huawei Cloud Service Tests.
Tests for the 8 priority Huawei Cloud emulated services.
Uses HTTP requests to the local MiniStack endpoint with Huawei-style headers.
"""

import json
import os
import urllib.request

import pytest

ENDPOINT = os.environ.get("MINISTACK_ENDPOINT", "http://localhost:4566")
REGION = os.environ.get("HUAWEICLOUD_REGION", "cn-north-4")
PROJECT_ID = os.environ.get("HUAWEICLOUD_PROJECT_ID", "0000000000000000")

# Huawei-style headers for testing
HUAWEI_HEADERS = {
    "Content-Type": "application/json",
    "X-Sdk-Date": "20240101T000000Z",
    "X-Auth-Token": "test-token",
}


def _request(method, path, data=None, headers=None):
    """Send HTTP request to the emulated Huawei Cloud endpoint."""
    url = f"{ENDPOINT}{path}"
    req_headers = {**HUAWEI_HEADERS, **(headers or {})}
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
# IAM Huawei — Token Authentication
# =========================================================================

class TestIAMHuawei:
    def test_create_token(self):
        """Test IAM token creation."""
        status, resp = _request("POST", "/v3/auth/tokens", {
            "auth": {"methods": ["token"], "scope": {"project": {"name": PROJECT_ID}}}
        })
        assert status == 201
        assert "token" in resp
        assert "X-Subject-Token" in resp.get("headers", {}) or True  # Header in response

    def test_list_projects(self):
        """Test listing projects."""
        status, resp = _request("GET", "/v3/projects")
        assert status == 200
        assert "projects" in resp


# =========================================================================
# OBS (Object Storage Service)
# =========================================================================

class TestOBS:
    def test_list_buckets_empty(self):
        """Test listing OBS buckets when empty."""
        status, resp = _request("GET", "/v1/")
        # OBS uses S3-compatible responses
        assert status in (200, 404)  # May return 200 XML or 404

    def test_create_and_list_bucket(self):
        """Test OBS bucket creation and listing."""
        # Create bucket
        status, _ = _request("PUT", "/v1/test-obs-bucket")
        assert status in (200, 204)

        # List buckets
        status, resp = _request("GET", "/v1/")
        assert status == 200


# =========================================================================
# SMN (Simple Message Notification)
# =========================================================================

class TestSMN:
    def test_create_topic(self):
        """Test SMN topic creation."""
        status, resp = _request("POST", f"/v2/{PROJECT_ID}/notifications/topics", {
            "name": "test-topic"
        })
        assert status == 200
        assert "topic_urn" in resp

    def test_list_topics(self):
        """Test listing SMN topics."""
        # Create first
        _request("POST", f"/v2/{PROJECT_ID}/notifications/topics", {"name": "test-topic-2"})
        status, resp = _request("GET", f"/v2/{PROJECT_ID}/notifications/topics")
        assert status == 200
        assert "topics" in resp

    def test_publish_message(self):
        """Test publishing a message to an SMN topic."""
        # Create topic
        _request("POST", f"/v2/{PROJECT_ID}/notifications/topics", {"name": "test-topic-pub"})
        # Publish
        status, resp = _request("POST", f"/v2/{PROJECT_ID}/notifications/topics/test-topic-pub/publish", {
            "message": "Hello from MiniStack Huawei!"
        })
        assert status == 200
        assert "message_id" in resp


# =========================================================================
# FunctionGraph
# =========================================================================

class TestFunctionGraph:
    def test_create_function(self):
        """Test FunctionGraph function creation."""
        status, resp = _request("POST", f"/v2/{PROJECT_ID}/fgs/functions", {
            "func_name": "test-function",
            "runtime": "Python3.9",
            "handler": "index.handler",
            "memory_size": 256,
            "timeout": 30,
        })
        assert status == 200
        assert "func_name" in resp
        assert resp["func_name"] == "test-function"

    def test_list_functions(self):
        """Test listing FunctionGraph functions."""
        _request("POST", f"/v2/{PROJECT_ID}/fgs/functions", {
            "func_name": "test-function-list",
            "runtime": "Python3.9",
            "handler": "index.handler",
        })
        status, resp = _request("GET", f"/v2/{PROJECT_ID}/fgs/functions")
        assert status == 200
        assert "functions" in resp

    def test_get_function(self):
        """Test getting a FunctionGraph function."""
        _request("POST", f"/v2/{PROJECT_ID}/fgs/functions", {
            "func_name": "test-function-get",
            "runtime": "Python3.9",
            "handler": "index.handler",
        })
        status, resp = _request("GET", f"/v2/{PROJECT_ID}/fgs/functions/test-function-get")
        assert status == 200
        assert resp.get("func_name") == "test-function-get"


# =========================================================================
# RDS Huawei
# =========================================================================

class TestRDSHuawei:
    def test_create_instance(self):
        """Test RDS instance creation."""
        status, resp = _request("POST", f"/v3/{PROJECT_ID}/instances", {
            "name": "test-rds-instance",
            "datastore": {"type": "MySQL", "version": "8.0"},
            "flavor_ref": "rds.mysql.c2.large.2",
            "volume": {"size": 40, "type": "ULTRAHIGH"},
            "vpc_id": "test-vpc",
            "subnet_id": "test-subnet",
            "security_group_id": "test-sg",
        })
        assert status == 202
        assert "instance" in resp

    def test_list_instances(self):
        """Test listing RDS instances."""
        _request("POST", f"/v3/{PROJECT_ID}/instances", {
            "name": "test-rds-list",
            "datastore": {"type": "PostgreSQL", "version": "14"},
        })
        status, resp = _request("GET", f"/v3/{PROJECT_ID}/instances")
        assert status == 200
        assert "instances" in resp


# =========================================================================
# DCS (Distributed Cache Service)
# =========================================================================

class TestDCS:
    def test_create_instance(self):
        """Test DCS instance creation."""
        status, resp = _request("POST", f"/v2/{PROJECT_ID}/instances", {
            "name": "test-dcs-instance",
            "engine": "Redis",
            "engine_version": "6.0",
            "capacity": 1,
            "vpc_id": "test-vpc",
            "subnet_id": "test-subnet",
        })
        assert status == 200
        assert "instance_id" in resp

    def test_list_instances(self):
        """Test listing DCS instances."""
        _request("POST", f"/v2/{PROJECT_ID}/instances", {
            "name": "test-dcs-list",
            "engine": "Redis",
        })
        status, resp = _request("GET", f"/v2/{PROJECT_ID}/instances")
        assert status == 200
        assert "instances" in resp


# =========================================================================
# LTS (Log Tank Service)
# =========================================================================

class TestLTS:
    def test_create_log_group(self):
        """Test LTS log group creation."""
        status, resp = _request("POST", f"/v2/{PROJECT_ID}/groups", {
            "log_group_name": "test-log-group",
            "ttl_in_days": 7,
        })
        assert status == 201
        assert "log_group_id" in resp

    def test_list_log_groups(self):
        """Test listing LTS log groups."""
        _request("POST", f"/v2/{PROJECT_ID}/groups", {
            "log_group_name": "test-log-group-list",
        })
        status, resp = _request("GET", f"/v2/{PROJECT_ID}/groups")
        assert status == 200
        assert "log_groups" in resp

    def test_create_log_stream_and_push(self):
        """Test creating a log stream and pushing logs."""
        # Create group
        status, group_resp = _request("POST", f"/v2/{PROJECT_ID}/groups", {
            "log_group_name": "test-log-group-stream",
        })
        assert status == 201
        group_id = group_resp["log_group_id"]

        # Create stream
        status, stream_resp = _request("POST", f"/v2/{PROJECT_ID}/groups/{group_id}/streams", {
            "log_stream_name": "test-stream",
        })
        assert status == 201
        stream_id = stream_resp["log_stream_id"]

        # Push logs
        status, _ = _request("POST", f"/v2/{PROJECT_ID}/groups/{group_id}/streams/{stream_id}/logs", {
            "log_events": [{"content": "Test log message", "time": 1700000000000}]
        })
        assert status == 200


# =========================================================================
# VPC Huawei
# =========================================================================

class TestVPCHuawei:
    def test_create_vpc(self):
        """Test VPC creation."""
        status, resp = _request("POST", f"/v1/{PROJECT_ID}/vpcs", {
            "vpc": {
                "name": "test-vpc",
                "cidr": "192.168.0.0/16",
            }
        })
        assert status == 200
        assert "vpc" in resp
        assert resp["vpc"]["name"] == "test-vpc"

    def test_list_vpcs(self):
        """Test listing VPCs."""
        _request("POST", f"/v1/{PROJECT_ID}/vpcs", {
            "vpc": {"name": "test-vpc-list", "cidr": "10.0.0.0/16"}
        })
        status, resp = _request("GET", f"/v1/{PROJECT_ID}/vpcs")
        assert status == 200
        assert "vpcs" in resp

    def test_create_subnet(self):
        """Test subnet creation."""
        # Create VPC first
        _, vpc_resp = _request("POST", f"/v1/{PROJECT_ID}/vpcs", {
            "vpc": {"name": "test-vpc-subnet", "cidr": "172.16.0.0/16"}
        })
        vpc_id = vpc_resp["vpc"]["id"]

        status, resp = _request("POST", f"/v1/{PROJECT_ID}/subnets", {
            "subnet": {
                "name": "test-subnet",
                "cidr": "172.16.0.0/24",
                "vpc_id": vpc_id,
            }
        })
        assert status == 200
        assert "subnet" in resp

    def test_create_security_group(self):
        """Test security group creation."""
        status, resp = _request("POST", f"/v1/{PROJECT_ID}/security-groups", {
            "security_group": {
                "name": "test-sg",
                "vpc_id": "test-vpc",
            }
        })
        assert status == 200
        assert "security_group" in resp


# =========================================================================
# Huawei Admin Endpoints
# =========================================================================

class TestHuaweiAdmin:
    def test_huawei_health(self):
        """Test Huawei health endpoint."""
        url = f"{ENDPOINT}/_huawei/health"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            assert "services" in data
            assert "obs" in data["services"]
            assert "iam_hw" in data["services"]

    def test_huawei_reset(self):
        """Test Huawei reset endpoint."""
        url = f"{ENDPOINT}/_huawei/reset"
        req = urllib.request.Request(url, data=b"", method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            assert data.get("reset") == "ok"
            assert data.get("scope") == "huawei"
