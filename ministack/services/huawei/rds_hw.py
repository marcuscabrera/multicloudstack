"""
RDS Huawei Cloud Service Emulator.
Reuses the existing RDS logic with Huawei Cloud API format.

Paths: /v3/{project_id}/instances
Supports: Instance CRUD, DescribeDBInstances, CreateDBInstance, DeleteDBInstance
"""

import copy
import json
import logging
import os
import time

from ministack.core.auth_huawei import HUAWEICLOUD_PROJECT_ID, HUAWEICLOUD_REGION
from ministack.core.persistence import load_state, PERSIST_STATE
from ministack.core.responses import AccountScopedDict, new_uuid

logger = logging.getLogger("rds_hw")

REGION = os.environ.get("HUAWEICLOUD_REGION", HUAWEICLOUD_REGION)
PROJECT_ID = os.environ.get("HUAWEICLOUD_PROJECT_ID", HUAWEICLOUD_PROJECT_ID)

_instances = AccountScopedDict()

# ── Persistence ────────────────────────────────────────────

def get_state():
    return {"instances": copy.deepcopy(_instances)}

def restore_state(data):
    if data:
        _instances.update(data.get("instances", {}))

_restored = load_state("rds_hw")
if _restored:
    restore_state(_restored)


async def handle_request(method: str, path: str, headers: dict, body: bytes, query_params: dict) -> tuple:
    """Handle RDS Huawei request."""

    # POST /v3/{proj}/instances — Create instance
    if path.endswith("/instances") and method == "POST":
        return _create_instance(body)

    # GET /v3/{proj}/instances — List instances
    if path.endswith("/instances") and method == "GET":
        return _list_instances()

    # GET /v3/{proj}/instances/{id} — Describe instance
    if "/instances/" in path and method == "GET":
        inst_id = path.split("/instances/")[-1]
        return _describe_instance(inst_id)

    # DELETE /v3/{proj}/instances/{id} — Delete instance
    if "/instances/" in path and method == "DELETE":
        inst_id = path.split("/instances/")[-1]
        return _delete_instance(inst_id)

    # POST /v3/{proj}/instances/{id}/action — Action (start/stop/reboot)
    if "/instances/" in path and "/action" in path and method == "POST":
        inst_id = path.split("/instances/")[1].split("/")[0]
        return _instance_action(inst_id, body)

    return 404, {"Content-Type": "application/json"}, json.dumps({
        "error_msg": "API not found", "error_code": "RDS.0001"
    }).encode()


def _create_instance(body: bytes) -> tuple:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return 400, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": "Invalid JSON", "error_code": "RDS.0010"
        }).encode()

    name = payload.get("name", f"rds-{new_uuid()[:8]}")
    instance_id = new_uuid()

    datastore = payload.get("datastore", {})
    db_type = datastore.get("type", "MySQL")
    db_version = datastore.get("version", "8.0")

    flavor = payload.get("flavor_ref", "rds.mysql.c2.large.2")
    volume = payload.get("volume", {})
    volume_size = volume.get("size", 40)
    volume_type = volume.get("type", "ULTRAHIGH")

    vpc_id = payload.get("vpc_id", "")
    subnet_id = payload.get("subnet_id", "")
    security_group_id = payload.get("security_group_id", "")

    az = payload.get("availability_zone", f"{REGION}-a")

    instance = {
        "id": instance_id,
        "name": name,
        "status": "BUILDING",
        "datastore": {"type": db_type, "version": db_version},
        "flavor_ref": flavor,
        "volume": {"size": volume_size, "type": volume_type},
        "vpc_id": vpc_id,
        "subnet_id": subnet_id,
        "security_group_id": security_group_id,
        "availability_zone": az,
        "region": REGION,
        "port": 3306 if db_type == "MySQL" else 5432,
        "private_ips": [f"192.168.0.{hash(name) % 254 + 1}"],
        "public_ips": [],
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "db_user_name": payload.get("db_user_name", "root"),
        "charge_info": payload.get("charge_info", {"charge_mode": "postPaid"}),
    }

    _instances[instance_id] = instance

    return 202, {"Content-Type": "application/json"}, json.dumps({
        "job_id": new_uuid(),
        "instance": {
            "id": instance_id,
            "name": name,
            "status": "BUILDING",
        }
    }).encode()


def _list_instances() -> tuple:
    instances = list(_instances.values())
    for inst in instances:
        if inst["status"] == "BUILDING":
            inst["status"] = "ACTIVE"  # Auto-transition
    return 200, {"Content-Type": "application/json"}, json.dumps({
        "instances": instances,
        "total_count": len(instances),
    }).encode()


def _describe_instance(inst_id: str) -> tuple:
    inst = _instances.get(inst_id)
    if not inst:
        return 404, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"Instance not found: {inst_id}", "error_code": "RDS.0011"
        }).encode()
    if inst["status"] == "BUILDING":
        inst["status"] = "ACTIVE"
    return 200, {"Content-Type": "application/json"}, json.dumps({"instance": inst}).encode()


def _delete_instance(inst_id: str) -> tuple:
    if inst_id not in _instances:
        return 404, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"Instance not found: {inst_id}", "error_code": "RDS.0011"
        }).encode()
    del _instances[inst_id]
    return 202, {"Content-Type": "application/json"}, json.dumps({
        "job_id": new_uuid(),
    }).encode()


def _instance_action(inst_id: str, body: bytes) -> tuple:
    if inst_id not in _instances:
        return 404, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"Instance not found: {inst_id}", "error_code": "RDS.0011"
        }).encode()

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return 400, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": "Invalid JSON", "error_code": "RDS.0010"
        }).encode()

    action = payload.get("start", payload.get("stop", payload.get("reboot", "")))
    inst = _instances[inst_id]

    if action == "start":
        inst["status"] = "ACTIVE"
    elif action == "stop":
        inst["status"] = "SHUTDOWN"
    elif action == "reboot":
        inst["status"] = "REBOOTING"

    return 202, {"Content-Type": "application/json"}, json.dumps({
        "job_id": new_uuid(),
    }).encode()


def reset():
    """Reset RDS Huawei state."""
    _instances.clear()
