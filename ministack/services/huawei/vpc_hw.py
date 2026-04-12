"""
VPC Huawei Cloud Service Emulator.
Based on EC2 VPC/Subnet/Security group logic.

Paths: /v1/{project_id}/vpcs, /v1/{project_id}/subnets, /v1/{project_id}/security-groups
Supports: VPC, Subnet, Security Group CRUD
"""

import copy
import json
import logging
import os
import time

from ministack.core.auth_huawei import HUAWEICLOUD_PROJECT_ID, HUAWEICLOUD_REGION
from ministack.core.persistence import load_state, PERSIST_STATE
from ministack.core.responses import AccountScopedDict, new_uuid

logger = logging.getLogger("vpc_hw")

REGION = os.environ.get("HUAWEICLOUD_REGION", HUAWEICLOUD_REGION)
PROJECT_ID = os.environ.get("HUAWEICLOUD_PROJECT_ID", HUAWEICLOUD_PROJECT_ID)

_vpcs = AccountScopedDict()
_subnets = AccountScopedDict()
_security_groups = AccountScopedDict()

# ── Persistence ────────────────────────────────────────────

def get_state():
    return {
        "vpcs": copy.deepcopy(_vpcs),
        "subnets": copy.deepcopy(_subnets),
        "security_groups": copy.deepcopy(_security_groups),
    }

def restore_state(data):
    if data:
        _vpcs.update(data.get("vpcs", {}))
        _subnets.update(data.get("subnets", {}))
        _security_groups.update(data.get("security_groups", {}))

_restored = load_state("vpc_hw")
if _restored:
    restore_state(_restored)


async def handle_request(method: str, path: str, headers: dict, body: bytes, query_params: dict) -> tuple:
    """Handle VPC Huawei request."""

    # VPCs
    if path.endswith("/vpcs") and method == "POST":
        return _create_vpc(body)
    if path.endswith("/vpcs") and method == "GET":
        return _list_vpcs()
    if "/vpcs/" in path and method == "GET":
        vpc_id = path.split("/vpcs/")[-1]
        return _get_vpc(vpc_id)
    if "/vpcs/" in path and method == "DELETE":
        vpc_id = path.split("/vpcs/")[-1]
        return _delete_vpc(vpc_id)
    if "/vpcs/" in path and method == "PUT":
        vpc_id = path.split("/vpcs/")[-1]
        return _update_vpc(vpc_id, body)

    # Subnets
    if path.endswith("/subnets") and method == "POST":
        return _create_subnet(body)
    if path.endswith("/subnets") and method == "GET":
        return _list_subnets()
    if "/subnets/" in path and method == "GET":
        subnet_id = path.split("/subnets/")[-1]
        return _get_subnet(subnet_id)
    if "/subnets/" in path and method == "DELETE":
        subnet_id = path.split("/subnets/")[-1]
        return _delete_subnet(subnet_id)

    # Security Groups
    if path.endswith("/security-groups") and method == "POST":
        return _create_security_group(body)
    if path.endswith("/security-groups") and method == "GET":
        return _list_security_groups()
    if "/security-groups/" in path and method == "GET":
        sg_id = path.split("/security-groups/")[-1]
        return _get_security_group(sg_id)
    if "/security-groups/" in path and method == "DELETE":
        sg_id = path.split("/security-groups/")[-1]
        return _delete_security_group(sg_id)
    if "/security-groups/" in path and "/rules" in path and method == "POST":
        sg_id = path.split("/security-groups/")[1].split("/")[0]
        return _create_security_group_rule(sg_id, body)

    return 404, {"Content-Type": "application/json"}, json.dumps({
        "error_msg": "API not found", "error_code": "VPC.0001"
    }).encode()


def _create_vpc(body: bytes) -> tuple:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return 400, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": "Invalid JSON", "error_code": "VPC.0010"
        }).encode()

    vpc = payload.get("vpc", {})
    name = vpc.get("name", f"vpc-{new_uuid()[:8]}")
    cidr = vpc.get("cidr", "192.168.0.0/16")

    vpc_id = new_uuid()
    vpc_record = {
        "id": vpc_id,
        "name": name,
        "cidr": cidr,
        "status": "OK",
        "description": vpc.get("description", ""),
        "project_id": PROJECT_ID,
        "routes": [],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _vpcs[vpc_id] = vpc_record

    return 200, {"Content-Type": "application/json"}, json.dumps({"vpc": vpc_record}).encode()


def _list_vpcs() -> tuple:
    return 200, {"Content-Type": "application/json"}, json.dumps({
        "vpcs": list(_vpcs.values())
    }).encode()


def _get_vpc(vpc_id: str) -> tuple:
    vpc = _vpcs.get(vpc_id)
    if not vpc:
        return 404, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"VPC not found: {vpc_id}", "error_code": "VPC.0011"
        }).encode()
    return 200, {"Content-Type": "application/json"}, json.dumps({"vpc": vpc}).encode()


def _delete_vpc(vpc_id: str) -> tuple:
    if vpc_id not in _vpcs:
        return 404, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"VPC not found: {vpc_id}", "error_code": "VPC.0011"
        }).encode()
    del _vpcs[vpc_id]
    return 200, {"Content-Type": "application/json"}, json.dumps({}).encode()


def _update_vpc(vpc_id: str, body: bytes) -> tuple:
    if vpc_id not in _vpcs:
        return 404, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"VPC not found: {vpc_id}", "error_code": "VPC.0011"
        }).encode()
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return 400, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": "Invalid JSON", "error_code": "VPC.0010"
        }).encode()
    vpc = _vpcs[vpc_id]
    vpc.update(payload.get("vpc", {}))
    return 200, {"Content-Type": "application/json"}, json.dumps({"vpc": vpc}).encode()


def _create_subnet(body: bytes) -> tuple:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return 400, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": "Invalid JSON", "error_code": "VPC.0010"
        }).encode()

    subnet = payload.get("subnet", {})
    name = subnet.get("name", f"subnet-{new_uuid()[:8]}")
    cidr = subnet.get("cidr", "192.168.0.0/24")
    vpc_id = subnet.get("vpc_id", "")
    gateway_ip = subnet.get("gateway_ip", cidr.rsplit(".", 1)[0] + ".1")

    subnet_id = new_uuid()
    subnet_record = {
        "id": subnet_id,
        "name": name,
        "cidr": cidr,
        "vpc_id": vpc_id,
        "gateway_ip": gateway_ip,
        "status": "ACTIVE",
        "availability_zone": REGION,
        "dns_list": subnet.get("dns_list", ["100.125.4.25", "8.8.8.8"]),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _subnets[subnet_id] = subnet_record

    return 200, {"Content-Type": "application/json"}, json.dumps({"subnet": subnet_record}).encode()


def _list_subnets() -> tuple:
    return 200, {"Content-Type": "application/json"}, json.dumps({
        "subnets": list(_subnets.values())
    }).encode()


def _get_subnet(subnet_id: str) -> tuple:
    subnet = _subnets.get(subnet_id)
    if not subnet:
        return 404, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"Subnet not found: {subnet_id}", "error_code": "VPC.0012"
        }).encode()
    return 200, {"Content-Type": "application/json"}, json.dumps({"subnet": subnet}).encode()


def _delete_subnet(subnet_id: str) -> tuple:
    if subnet_id not in _subnets:
        return 404, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"Subnet not found: {subnet_id}", "error_code": "VPC.0012"
        }).encode()
    del _subnets[subnet_id]
    return 200, {"Content-Type": "application/json"}, json.dumps({}).encode()


def _create_security_group(body: bytes) -> tuple:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return 400, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": "Invalid JSON", "error_code": "VPC.0010"
        }).encode()

    sg = payload.get("security_group", {})
    name = sg.get("name", f"sg-{new_uuid()[:8]}")
    vpc_id = sg.get("vpc_id", "")

    sg_id = new_uuid()
    sg_record = {
        "id": sg_id,
        "name": name,
        "vpc_id": vpc_id,
        "description": sg.get("description", ""),
        "security_group_rules": [],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _security_groups[sg_id] = sg_record

    return 200, {"Content-Type": "application/json"}, json.dumps({"security_group": sg_record}).encode()


def _list_security_groups() -> tuple:
    return 200, {"Content-Type": "application/json"}, json.dumps({
        "security_groups": list(_security_groups.values())
    }).encode()


def _get_security_group(sg_id: str) -> tuple:
    sg = _security_groups.get(sg_id)
    if not sg:
        return 404, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"Security group not found: {sg_id}", "error_code": "VPC.0013"
        }).encode()
    return 200, {"Content-Type": "application/json"}, json.dumps({"security_group": sg}).encode()


def _delete_security_group(sg_id: str) -> tuple:
    if sg_id not in _security_groups:
        return 404, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"Security group not found: {sg_id}", "error_code": "VPC.0013"
        }).encode()
    del _security_groups[sg_id]
    return 200, {"Content-Type": "application/json"}, json.dumps({}).encode()


def _create_security_group_rule(sg_id: str, body: bytes) -> tuple:
    if sg_id not in _security_groups:
        return 404, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"Security group not found: {sg_id}", "error_code": "VPC.0013"
        }).encode()

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return 400, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": "Invalid JSON", "error_code": "VPC.0010"
        }).encode()

    rule = payload.get("security_group_rule", {})
    rule_id = new_uuid()
    rule_record = {
        "id": rule_id,
        "direction": rule.get("direction", "ingress"),
        "ethertype": rule.get("ethertype", "IPv4"),
        "protocol": rule.get("protocol", "tcp"),
        "port_range_min": rule.get("port_range_min"),
        "port_range_max": rule.get("port_range_max"),
        "remote_ip_prefix": rule.get("remote_ip_prefix", "0.0.0.0/0"),
    }
    _security_groups[sg_id]["security_group_rules"].append(rule_record)

    return 200, {"Content-Type": "application/json"}, json.dumps({
        "security_group_rule": rule_record
    }).encode()


def reset():
    """Reset VPC Huawei state."""
    _vpcs.clear()
    _subnets.clear()
    _security_groups.clear()
