"""
IAM Huawei Cloud Service Emulator.
Supports token-based authentication compatible with huaweicloudsdkcore.

Endpoints:
    POST /v3/auth/tokens          — Create token
    GET  /v3/auth/tokens          — Validate token
    GET  /v3/users                — List users
    GET  /v3/projects             — List projects
    GET  /v3/OS-CREDENTIAL/credentials/{ak} — Query credential info
"""

import json
import logging
import os

from ministack.core.auth_huawei import (
    HUAWEICLOUD_PROJECT_ID,
    HUAWEICLOUD_REGION,
    HUAWEICLOUD_SDK_AK,
    authenticate_token,
    create_token,
    register_credential,
)
from ministack.core.responses import new_uuid

logger = logging.getLogger("iam_hw")

_credentials_registered = False


def _ensure_default_credential():
    """Register the default test credential on first request."""
    global _credentials_registered
    if not _credentials_registered:
        register_credential(
            ak=HUAWEICLOUD_SDK_AK,
            sk=os.environ.get("HUAWEICLOUD_SDK_SK", "test"),
            project_id=HUAWEICLOUD_PROJECT_ID,
            region=HUAWEICLOUD_REGION,
        )
        _credentials_registered = True


async def handle_request(method: str, path: str, headers: dict, body: bytes, query_params: dict) -> tuple:
    """Handle IAM Huawei Cloud request."""
    _ensure_default_credential()

    # POST /v3/auth/tokens — Create token
    if path == "/v3/auth/tokens" and method == "POST":
        return _create_token(body, headers)

    # GET /v3/auth/tokens — Validate token
    if path == "/v3/auth/tokens" and method == "GET":
        return _validate_token(headers)

    # GET /v3/users — List users (stub)
    if path.startswith("/v3/users") and method == "GET":
        return _list_users()

    # GET /v3/projects — List projects (stub)
    if path.startswith("/v3/projects") and method == "GET":
        return _list_projects()

    # GET /v3/OS-CREDENTIAL/credentials/{ak} — Query AK info
    if path.startswith("/v3.0/OS-CREDENTIAL/credentials/") and method == "GET":
        ak = path.rsplit("/", 1)[-1]
        return _query_credential(ak)

    # Default: 404
    return 404, {"Content-Type": "application/json"}, json.dumps({
        "error_msg": "API not found",
        "error_code": "APIG.0301",
    }).encode()


def _create_token(body: bytes, headers: dict) -> tuple:
    """Create an IAM token (POST /v3/auth/tokens)."""
    try:
        payload = json.loads(body) if body else {}
    except json.JSONDecodeError:
        payload = {}

    # Extract auth from body
    identity = payload.get("auth", {})
    identity_methods = identity.get("methods", ["token"])
    scope = identity.get("scope", {})

    # Use default credentials if not specified
    token_info = create_token(
        ak=HUAWEICLOUD_SDK_AK,
        project_id=HUAWEICLOUD_PROJECT_ID,
    )

    if not token_info:
        return 401, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": "Authentication failed",
            "error_code": "IAM.0002",
        }).encode()

    resp_headers = {
        "Content-Type": "application/json",
        "X-Subject-Token": token_info["token_id"],
    }

    return 201, resp_headers, json.dumps(token_info).encode()


def _validate_token(headers: dict) -> tuple:
    """Validate an IAM token (GET /v3/auth/tokens)."""
    valid, token_info = authenticate_token(headers)
    if not valid:
        return 401, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": "Invalid token",
            "error_code": "IAM.0003",
        }).encode()

    resp_headers = {
        "Content-Type": "application/json",
        "X-Subject-Token": headers.get("x-auth-token", headers.get("X-Auth-Token", "")),
    }

    return 200, resp_headers, json.dumps(token_info).encode()


def _list_users() -> tuple:
    """List users (stub)."""
    return 200, {"Content-Type": "application/json"}, json.dumps({
        "users": [],
        "links": {"self": "/v3/users", "previous": None, "next": None},
    }).encode()


def _list_projects() -> tuple:
    """List projects (stub)."""
    return 200, {"Content-Type": "application/json"}, json.dumps({
        "projects": [
            {
                "id": HUAWEICLOUD_PROJECT_ID,
                "name": HUAWEICLOUD_PROJECT_ID,
                "domain_id": "huawei-emulated-domain-001",
                "parent_id": "huawei-emulated-domain-001",
                "description": "Emulated Huawei Cloud project",
                "enabled": True,
                "is_domain": False,
            }
        ],
        "links": {"self": "/v3/projects", "previous": None, "next": None},
    }).encode()


def _query_credential(ak: str) -> tuple:
    """Query credential info (stub)."""
    from ministack.core.auth_huawei import _credentials
    if ak not in _credentials:
        return 404, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": "Credential not found",
            "error_code": "IAM.0004",
        }).encode()

    cred = _credentials[ak]
    return 200, {"Content-Type": "application/json"}, json.dumps({
        "credential": {
            "access_key_id": ak,
            "status": "active",
            "create_time": "2024-01-01T00:00:00Z",
            "user_id": cred["user_id"],
            "description": "Emulated Huawei Cloud credential",
        }
    }).encode()


def reset():
    """Reset IAM Huawei state."""
    from ministack.core.auth_huawei import _tokens
    _tokens.clear()
