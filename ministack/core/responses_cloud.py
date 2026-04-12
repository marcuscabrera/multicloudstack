"""
Multi-cloud response helpers for Azure and Huawei Cloud.
Provides JSON/XML response formatting consistent with AWS helpers
but with cloud-specific header conventions.
"""

import json
import uuid
import time


def json_response(data: dict, status: int = 200, extra_headers: dict = None) -> tuple:
    """Generic JSON response with optional cloud-specific headers."""
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    return status, headers, body


def error_response(status: int, code: str, message: str, extra_headers: dict = None) -> tuple:
    """Generic error response."""
    body = json.dumps({"error": {"code": code, "message": message}}, ensure_ascii=False).encode()
    headers = {"Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    return status, headers, body


# ── Azure-specific helpers ──────────────────────────────────

def azure_json_response(data: dict, status: int = 200, request_id: str = None) -> tuple:
    """Azure-style JSON response with x-ms-request-id header."""
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return status, {
        "Content-Type": "application/json",
        "x-ms-request-id": request_id or str(uuid.uuid4()),
    }, body


def azure_error_response(status: int, code: str, message: str, request_id: str = None) -> tuple:
    """Azure-style error response."""
    body = json.dumps({
        "error": {
            "code": code,
            "message": message,
        }
    }).encode()
    return status, {
        "Content-Type": "application/json",
        "x-ms-request-id": request_id or str(uuid.uuid4()),
    }, body


# ── Huawei-specific helpers ─────────────────────────────────

def huawei_json_response(data: dict, status: int = 200, request_id: str = None) -> tuple:
    """Huawei Cloud JSON response with x-request-id header."""
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return status, {
        "Content-Type": "application/json",
        "x-request-id": request_id or str(uuid.uuid4()),
    }, body


def huawei_error_response(status: int, error_code: str, error_msg: str, request_id: str = None) -> tuple:
    """Huawei Cloud error response."""
    body = json.dumps({
        "error_code": error_code,
        "error_msg": error_msg,
        "request_id": request_id or str(uuid.uuid4()),
    }).encode()
    return status, {"Content-Type": "application/json"}, body


# ── ARM Resource ID builder ─────────────────────────────────

def arm_resource_id(subscription_id: str, resource_group: str,
                    provider: str, resource_type: str, name: str) -> str:
    """Build an ARM Resource ID string."""
    return f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/{provider}/{resource_type}/{name}"
