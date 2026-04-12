"""
LTS (Log Tank Service) — Huawei Cloud compatible.
Based on CloudWatch Logs implementation.

Paths: /v2/{project_id}/groups, /v2/{project_id}/streams, /v2/{project_id}/logs
Supports: Log group/stream CRUD, log event submission and querying
"""

import base64
import copy
import json
import logging
import os
import time

from ministack.core.auth_huawei import HUAWEICLOUD_PROJECT_ID, HUAWEICLOUD_REGION
from ministack.core.persistence import load_state, PERSIST_STATE
from ministack.core.responses import AccountScopedDict, new_uuid

logger = logging.getLogger("lts")

REGION = os.environ.get("HUAWEICLOUD_REGION", HUAWEICLOUD_REGION)
PROJECT_ID = os.environ.get("HUAWEICLOUD_PROJECT_ID", HUAWEICLOUD_PROJECT_ID)

_log_groups = AccountScopedDict()
# group_name -> {id, name, ttl_in_days, tags: {}, streams: {stream_name: {id, name, events: [], created_at}}}

# ── Persistence ────────────────────────────────────────────

def get_state():
    return {"log_groups": copy.deepcopy(_log_groups)}

def restore_state(data):
    if data:
        _log_groups.update(data.get("log_groups", {}))

_restored = load_state("lts")
if _restored:
    restore_state(_restored)


async def handle_request(method: str, path: str, headers: dict, body: bytes, query_params: dict) -> tuple:
    """Handle LTS request."""

    # POST /v2/{proj}/groups — Create log group
    if path.endswith("/groups") and method == "POST":
        return _create_log_group(body)

    # GET /v2/{proj}/groups — List log groups
    if path.endswith("/groups") and method == "GET":
        return _list_log_groups()

    # DELETE /v2/{proj}/groups/{id} — Delete log group
    if "/groups/" in path and method == "DELETE":
        group_id = path.split("/groups/")[-1]
        return _delete_log_group(group_id)

    # POST /v2/{proj}/groups/{group_id}/streams — Create log stream
    if "/groups/" in path and path.endswith("/streams") and method == "POST":
        group_id = path.split("/groups/")[1].split("/")[0]
        return _create_log_stream(group_id, body)

    # GET /v2/{proj}/groups/{group_id}/streams — List log streams
    if "/groups/" in path and path.endswith("/streams") and method == "GET":
        group_id = path.split("/groups/")[1].split("/")[0]
        return _list_log_streams(group_id)

    # POST /v2/{proj}/groups/{group_id}/streams/{stream_id}/logs — Push logs
    if "/streams/" in path and path.endswith("/logs") and method == "POST":
        parts = path.split("/streams/")
        stream_id = parts[1].split("/")[0]
        return _push_logs(stream_id, body)

    # GET /v2/{proj}/groups/{group_id}/streams/{stream_id}/logs — List logs
    if "/streams/" in path and path.endswith("/logs") and method == "GET":
        stream_id = path.split("/streams/")[1].split("/")[0]
        return _list_logs(stream_id, query_params)

    return 404, {"Content-Type": "application/json"}, json.dumps({
        "error_msg": "API not found", "error_code": "LTS.0001"
    }).encode()


def _create_log_group(body: bytes) -> tuple:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return 400, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": "Invalid JSON", "error_code": "LTS.0010"
        }).encode()

    name = payload.get("log_group_name", f"log-group-{new_uuid()[:8]}")
    ttl = payload.get("ttl_in_days", 7)

    group_id = new_uuid()
    group = {
        "id": group_id,
        "name": name,
        "ttl_in_days": ttl,
        "tags": [],
        "streams": {},
        "created_at": int(time.time() * 1000),
    }
    _log_groups[name] = group

    return 201, {"Content-Type": "application/json"}, json.dumps({
        "log_group_id": group_id,
    }).encode()


def _list_log_groups() -> tuple:
    groups = []
    for name, g in _log_groups.items():
        gc = copy.deepcopy(g)
        gc.pop("streams", None)  # Don't include streams in list
        groups.append(gc)
    return 200, {"Content-Type": "application/json"}, json.dumps({
        "log_groups": groups,
        "total": len(groups),
    }).encode()


def _delete_log_group(group_id: str) -> tuple:
    for name, g in list(_log_groups.items()):
        if g["id"] == group_id:
            del _log_groups[name]
            return 200, {"Content-Type": "application/json"}, json.dumps({}).encode()
    return 404, {"Content-Type": "application/json"}, json.dumps({
        "error_msg": f"Log group not found: {group_id}", "error_code": "LTS.0011"
    }).encode()


def _create_log_stream(group_id: str, body: bytes) -> tuple:
    group = None
    for g in _log_groups.values():
        if g["id"] == group_id:
            group = g
            break
    if not group:
        return 404, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"Log group not found: {group_id}", "error_code": "LTS.0011"
        }).encode()

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return 400, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": "Invalid JSON", "error_code": "LTS.0010"
        }).encode()

    name = payload.get("log_stream_name", f"log-stream-{new_uuid()[:8]}")
    stream_id = new_uuid()
    stream = {
        "id": stream_id,
        "name": name,
        "events": [],
        "created_at": int(time.time() * 1000),
    }
    group["streams"][name] = stream

    return 201, {"Content-Type": "application/json"}, json.dumps({
        "log_stream_id": stream_id,
    }).encode()


def _list_log_streams(group_id: str) -> tuple:
    for g in _log_groups.values():
        if g["id"] == group_id:
            streams = [
                {"id": s["id"], "name": s["name"], "created_at": s["created_at"]}
                for s in g["streams"].values()
            ]
            return 200, {"Content-Type": "application/json"}, json.dumps({
                "log_streams": streams,
                "total": len(streams),
            }).encode()
    return 404, {"Content-Type": "application/json"}, json.dumps({
        "error_msg": f"Log group not found: {group_id}", "error_code": "LTS.0011"
    }).encode()


def _push_logs(stream_id: str, body: bytes) -> tuple:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return 400, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": "Invalid JSON", "error_code": "LTS.0010"
        }).encode()

    log_events = payload.get("log_events", [])
    if not log_events:
        # Try alternate format
        logs = payload.get("logs", [])
        if logs:
            log_events = [{"content": log, "time": int(time.time() * 1000)} for log in logs]

    # Find the stream
    for g in _log_groups.values():
        for s in g["streams"].values():
            if s["id"] == stream_id:
                for event in log_events:
                    s["events"].append({
                        "content": event.get("content", event.get("message", "")),
                        "time": event.get("time", int(time.time() * 1000)),
                        "line_num": len(s["events"]) + 1,
                    })
                return 200, {"Content-Type": "application/json"}, json.dumps({
                    "log_write_time": int(time.time() * 1000),
                    "reason": None,
                }).encode()

    return 404, {"Content-Type": "application/json"}, json.dumps({
        "error_msg": f"Log stream not found: {stream_id}", "error_code": "LTS.0012"
    }).encode()


def _list_logs(stream_id: str, query_params: dict) -> tuple:
    for g in _log_groups.values():
        for s in g["streams"].values():
            if s["id"] == stream_id:
                events = s["events"]
                # Simple pagination
                limit = int(query_params.get("limit", [100])[0]) if isinstance(query_params.get("limit"), list) else 100
                return 200, {"Content-Type": "application/json"}, json.dumps({
                    "logs": events[:limit],
                    "total": len(events),
                }).encode()
    return 404, {"Content-Type": "application/json"}, json.dumps({
        "error_msg": f"Log stream not found: {stream_id}", "error_code": "LTS.0012"
    }).encode()


def reset():
    """Reset LTS state."""
    _log_groups.clear()
