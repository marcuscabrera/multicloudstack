"""
Extended Huawei Cloud Service Stubs.
Each module provides a minimal handle_request + reset + get_state pattern
for services that map to existing AWS implementations.
"""

import copy
import json
import logging
import os
import time

from ministack.core.auth_huawei import HUAWEICLOUD_PROJECT_ID, HUAWEICLOUD_REGION
from ministack.core.persistence import load_state, PERSIST_STATE
from ministack.core.responses import AccountScopedDict, new_uuid

logger = logging.getLogger("huawei_extended")

REGION = os.environ.get("HUAWEICLOUD_REGION", HUAWEICLOUD_REGION)
PROJECT_ID = os.environ.get("HUAWEICLOUD_PROJECT_ID", HUAWEICLOUD_PROJECT_ID)

# ---- DMS (Distributed Message Service) ----
_dms_queues = AccountScopedDict()

async def handle_dms_request(method, path, headers, body, query_params):
    if path.endswith("/queues") and method == "POST":
        payload = json.loads(body) if body else {}
        name = payload.get("name", f"queue-{new_uuid()[:8]}")
        q = {"id": new_uuid(), "name": name, "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        _dms_queues[q["id"]] = q
        return 200, {"Content-Type": "application/json"}, json.dumps(q).encode()
    if path.endswith("/queues") and method == "GET":
        return 200, {"Content-Type": "application/json"}, json.dumps({"queues": list(_dms_queues.values())}).encode()
    return 404, {"Content-Type": "application/json"}, json.dumps({"error_msg": "Not found", "error_code": "DMS.0001"}).encode()

def reset_dms():
    _dms_queues.clear()

# ---- AOM (Application Operations Management) ----
_aom_metrics = AccountScopedDict()

async def handle_aom_request(method, path, headers, body, query_params):
    if path.endswith("/metrics") and method == "POST":
        payload = json.loads(body) if body else {}
        metric_id = new_uuid()
        _aom_metrics[metric_id] = {"id": metric_id, "data": payload, "timestamp": int(time.time() * 1000)}
        return 200, {"Content-Type": "application/json"}, json.dumps({"metric_id": metric_id}).encode()
    if path.endswith("/metrics") and method == "GET":
        return 200, {"Content-Type": "application/json"}, json.dumps({"metrics": list(_aom_metrics.values())}).encode()
    return 404, {"Content-Type": "application/json"}, json.dumps({"error_msg": "Not found", "error_code": "AOM.0001"}).encode()

def reset_aom():
    _aom_metrics.clear()

# ---- ECS Huawei (Elastic Cloud Server) ----
_ecs_servers = AccountScopedDict()

async def handle_ecs_request(method, path, headers, body, query_params):
    if path.endswith("/cloudservers") and method == "POST":
        payload = json.loads(body) if body else {}
        server = payload.get("server", {})
        name = server.get("name", f"ecs-{new_uuid()[:8]}")
        srv_id = new_uuid()
        srv = {
            "id": srv_id, "name": name, "status": "BUILD",
            "flavor": server.get("flavorRef", {}),
            "imageRef": server.get("imageRef", ""),
            "addresses": {},
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        _ecs_servers[srv_id] = srv
        return 200, {"Content-Type": "application/json"}, json.dumps({"server": srv, "job_id": new_uuid()}).encode()
    if path.endswith("/cloudservers") and method == "GET":
        return 200, {"Content-Type": "application/json"}, json.dumps({"servers": list(_ecs_servers.values())}).encode()
    return 404, {"Content-Type": "application/json"}, json.dumps({"error_msg": "Not found", "error_code": "ECS.0001"}).encode()

def reset_ecs():
    _ecs_servers.clear()

# ---- APIG (API Gateway Huawei) ----
_apig_apis = AccountScopedDict()

async def handle_apig_request(method, path, headers, body, query_params):
    if "/apigw" in path and method == "POST" and path.endswith("/instances"):
        payload = json.loads(body) if body else {}
        name = payload.get("name", f"apig-{new_uuid()[:8]}")
        api = {"id": new_uuid(), "name": name, "status": "running", "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        _apig_apis[api["id"]] = api
        return 200, {"Content-Type": "application/json"}, json.dumps(api).encode()
    if "/apigw" in path and method == "GET" and path.endswith("/instances"):
        return 200, {"Content-Type": "application/json"}, json.dumps({"instances": list(_apig_apis.values())}).encode()
    return 404, {"Content-Type": "application/json"}, json.dumps({"error_msg": "Not found", "error_code": "APIG.0001"}).encode()

def reset_apig():
    _apig_apis.clear()

# ---- DIS (Data Ingestion Service) ----
_dis_streams = AccountScopedDict()

async def handle_dis_request(method, path, headers, body, query_params):
    if path.endswith("/streams") and method == "POST":
        payload = json.loads(body) if body else {}
        name = payload.get("stream_name", f"dis-{new_uuid()[:8]}")
        stream = {"stream_id": new_uuid(), "stream_name": name, "status": "RUNNING", "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        _dis_streams[stream["stream_id"]] = stream
        return 200, {"Content-Type": "application/json"}, json.dumps({"stream_id": stream["stream_id"]}).encode()
    if path.endswith("/streams") and method == "GET":
        return 200, {"Content-Type": "application/json"}, json.dumps({"streams": list(_dis_streams.values())}).encode()
    return 404, {"Content-Type": "application/json"}, json.dumps({"error_msg": "Not found", "error_code": "DIS.0001"}).encode()

def reset_dis():
    _dis_streams.clear()

# ---- KMS Huawei ----
_kms_keys = AccountScopedDict()

async def handle_kms_request(method, path, headers, body, query_params):
    if path.endswith("/keys") and method == "POST":
        payload = json.loads(body) if body else {}
        key = {
            "key_id": new_uuid(),
            "key_alias": payload.get("key_alias", f"key-{new_uuid()[:8]}"),
            "key_state": "2",  # Enabled
            "creation_date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "realm": REGION,
        }
        _kms_keys[key["key_id"]] = key
        return 200, {"Content-Type": "application/json"}, json.dumps(key).encode()
    if path.endswith("/keys") and method == "GET":
        return 200, {"Content-Type": "application/json"}, json.dumps({"keys": list(_kms_keys.values())}).encode()
    return 404, {"Content-Type": "application/json"}, json.dumps({"error_msg": "Not found", "error_code": "KMS.0001"}).encode()

def reset_kms():
    _kms_keys.clear()

# ---- CSMS (Cloud Secret Management Service) ----
_csms_secrets = AccountScopedDict()

async def handle_csms_request(method, path, headers, body, query_params):
    if path.endswith("/secrets") and method == "POST":
        payload = json.loads(body) if body else {}
        name = payload.get("name", f"secret-{new_uuid()[:8]}")
        secret = {
            "id": new_uuid(),
            "name": name,
            "status": "ENABLED",
            "create_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        _csms_secrets[name] = secret
        return 200, {"Content-Type": "application/json"}, json.dumps(secret).encode()
    if path.endswith("/secrets") and method == "GET":
        return 200, {"Content-Type": "application/json"}, json.dumps({"secrets": list(_csms_secrets.values())}).encode()
    return 404, {"Content-Type": "application/json"}, json.dumps({"error_msg": "Not found", "error_code": "CSMS.0001"}).encode()

def reset_csms():
    _csms_secrets.clear()

# ---- CCE (Cloud Container Engine) ----
_cce_clusters = AccountScopedDict()

async def handle_cce_request(method, path, headers, body, query_params):
    if path.endswith("/clusters") and method == "POST":
        payload = json.loads(body) if body else {}
        name = payload.get("metadata", {}).get("name", f"cce-{new_uuid()[:8]}")
        cluster = {
            "metadata": {"name": name, "uid": new_uuid()},
            "spec": payload.get("spec", {}),
            "status": {"phase": "Available"},
            "kind": "Cluster",
            "apiVersion": "v3",
        }
        _cce_clusters[cluster["metadata"]["uid"]] = cluster
        return 200, {"Content-Type": "application/json"}, json.dumps(cluster).encode()
    if path.endswith("/clusters") and method == "GET":
        items = {"kind": "List", "apiVersion": "v3", "items": list(_cce_clusters.values())}
        return 200, {"Content-Type": "application/json"}, json.dumps(items).encode()
    return 404, {"Content-Type": "application/json"}, json.dumps({"error_msg": "Not found", "error_code": "CCE.0001"}).encode()

def reset_cce():
    _cce_clusters.clear()

# ---- RFS (Resource Formation Service) ----
_rfs_stacks = AccountScopedDict()

async def handle_rfs_request(method, path, headers, body, query_params):
    if path.endswith("/stacks") and method == "POST":
        payload = json.loads(body) if body else {}
        name = payload.get("stack_name", f"rfs-{new_uuid()[:8]}")
        stack = {
            "id": new_uuid(),
            "stack_name": name,
            "status": "CREATE_IN_PROGRESS",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        _rfs_stacks[stack["id"]] = stack
        return 200, {"Content-Type": "application/json"}, json.dumps(stack).encode()
    if path.endswith("/stacks") and method == "GET":
        return 200, {"Content-Type": "application/json"}, json.dumps({"stacks": list(_rfs_stacks.values())}).encode()
    return 404, {"Content-Type": "application/json"}, json.dumps({"error_msg": "Not found", "error_code": "RFS.0001"}).encode()

def reset_rfs():
    _rfs_stacks.clear()
