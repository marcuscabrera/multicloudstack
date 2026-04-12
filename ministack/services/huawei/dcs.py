"""
DCS (Distributed Cache Service) — Huawei Cloud compatible.
Based on existing ElastiCache implementation.

Paths: /v1.0/{project_id}/instances  or  /v2/{project_id}/instances
Supports: Instance CRUD, Redis/Memcached cluster management
"""

import copy
import json
import logging
import os
import time

from ministack.core.auth_huawei import HUAWEICLOUD_PROJECT_ID, HUAWEICLOUD_REGION
from ministack.core.persistence import load_state, PERSIST_STATE
from ministack.core.responses import AccountScopedDict, new_uuid

logger = logging.getLogger("dcs")

REGION = os.environ.get("HUAWEICLOUD_REGION", HUAWEICLOUD_REGION)
PROJECT_ID = os.environ.get("HUAWEICLOUD_PROJECT_ID", HUAWEICLOUD_PROJECT_ID)

_instances = AccountScopedDict()

# ── Persistence ────────────────────────────────────────────

def get_state():
    return {"instances": copy.deepcopy(_instances)}

def restore_state(data):
    if data:
        _instances.update(data.get("instances", {}))

_restored = load_state("dcs")
if _restored:
    restore_state(_restored)


async def handle_request(method: str, path: str, headers: dict, body: bytes, query_params: dict) -> tuple:
    """Handle DCS request."""

    # POST /v1.0/{proj}/instances or /v2/{proj}/instances — Create
    if path.endswith("/instances") and method == "POST":
        return _create_instance(body)

    # GET /v1.0/{proj}/instances or /v2/{proj}/instances — List
    if path.endswith("/instances") and method == "GET":
        return _list_instances()

    # GET /v1.0/{proj}/instances/{id} — Describe
    if "/instances/" in path and method == "GET":
        inst_id = path.split("/instances/")[-1]
        return _describe_instance(inst_id)

    # DELETE /v1.0/{proj}/instances/{id} — Delete
    if "/instances/" in path and method == "DELETE":
        inst_id = path.split("/instances/")[-1]
        return _delete_instance(inst_id)

    # PUT /v1.0/{proj}/instances/{id} — Modify
    if "/instances/" in path and method == "PUT":
        inst_id = path.split("/instances/")[-1]
        return _modify_instance(inst_id, body)

    return 404, {"Content-Type": "application/json"}, json.dumps({
        "error_msg": "API not found", "error_code": "DCS.0001"
    }).encode()


def _create_instance(body: bytes) -> tuple:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return 400, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": "Invalid JSON", "error_code": "DCS.0010"
        }).encode()

    name = payload.get("name", f"dcs-{new_uuid()[:8]}")
    instance_id = new_uuid()

    engine = payload.get("engine", "Redis")
    engine_version = payload.get("engine_version", "6.0")
    capacity = payload.get("capacity", 1)  # GB
    spec_code = payload.get("spec_code", "dcs.master_standby")

    az = payload.get("availability_zones", [f"{REGION}-a"])
    vpc_id = payload.get("vpc_id", "")
    subnet_id = payload.get("subnet_id", "")
    security_group_id = payload.get("security_group_id", "")

    password = payload.get("password", "")
    no_password_access = payload.get("no_password_access", not password)

    instance = {
        "instance_id": instance_id,
        "name": name,
        "engine": engine,
        "engine_version": engine_version,
        "capacity": capacity,
        "spec_code": spec_code,
        "status": "CREATING",
        "availability_zones": az,
        "vpc_id": vpc_id,
        "subnet_id": subnet_id,
        "security_group_id": security_group_id,
        "ip": f"192.168.0.{hash(name) % 254 + 1}",
        "port": 6379,
        "no_password_access": no_password_access,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "max_clients": 10000,
        "domain_name": f"{instance_id}.dcs.huawei.com",
    }

    _instances[instance_id] = instance

    return 200, {"Content-Type": "application/json"}, json.dumps({
        "instance_id": instance_id,
        "order_id": new_uuid(),
    }).encode()


def _list_instances() -> tuple:
    instances = list(_instances.values())
    for inst in instances:
        if inst["status"] == "CREATING":
            inst["status"] = "RUNNING"
    return 200, {"Content-Type": "application/json"}, json.dumps({
        "instances": instances,
        "instance_num": len(instances),
    }).encode()


def _describe_instance(inst_id: str) -> tuple:
    inst = _instances.get(inst_id)
    if not inst:
        return 404, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"Instance not found: {inst_id}", "error_code": "DCS.0011"
        }).encode()
    if inst["status"] == "CREATING":
        inst["status"] = "RUNNING"
    return 200, {"Content-Type": "application/json"}, json.dumps({"instances": [inst]}).encode()


def _delete_instance(inst_id: str) -> tuple:
    if inst_id not in _instances:
        return 404, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"Instance not found: {inst_id}", "error_code": "DCS.0011"
        }).encode()
    del _instances[inst_id]
    return 200, {"Content-Type": "application/json"}, json.dumps({
        "instance_id": inst_id,
        "result": "success",
    }).encode()


def _modify_instance(inst_id: str, body: bytes) -> tuple:
    if inst_id not in _instances:
        return 404, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"Instance not found: {inst_id}", "error_code": "DCS.0011"
        }).encode()

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return 400, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": "Invalid JSON", "error_code": "DCS.0010"
        }).encode()

    inst = _instances[inst_id]
    for key in ["name", "port", "security_group_id"]:
        if key in payload:
            inst[key] = payload[key]
    inst["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    return 200, {"Content-Type": "application/json"}, json.dumps({
        "instance_id": inst_id,
        "result": "success",
    }).encode()


def reset():
    """Reset DCS state."""
    _instances.clear()
