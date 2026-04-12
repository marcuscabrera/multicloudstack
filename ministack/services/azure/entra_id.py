"""
Azure Entra ID / AAD — OAuth 2.0 token endpoint.
Compatible with azure-identity ClientSecretCredential.

Endpoints:
    POST /tenant/{tid}/oauth2/v2.0/token
    GET  /tenant/{tid}/.well-known/openid-configuration
    GET  /tenant/{tid}/discovery/v2.0/keys
"""

import json
import logging
import os
import time

from ministack.core.auth_azure import (
    AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET,
    issue_token, register_credential,
)
from ministack.core.responses import new_uuid

logger = logging.getLogger("entra_id")

# ── Persistence ────────────────────────────────────────────
_tokens_issued = []

async def handle_request(method: str, path: str, headers: dict, body: bytes, query_params: dict) -> tuple:
    """Handle Entra ID / AAD request."""
    # Ensure default credential
    register_credential(AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID)

    # POST /tenant/{tid}/oauth2/v2.0/token
    if "/oauth2/v2.0/token" in path and method == "POST":
        return _issue_token(body, path, headers, query_params)

    # GET /tenant/{tid}/.well-known/openid-configuration
    if "/.well-known/openid-configuration" in path and method == "GET":
        return _openid_config(path)

    # GET /tenant/{tid}/discovery/v2.0/keys
    if "/discovery/v2.0/keys" in path and method == "GET":
        return _jwks(path)

    # GET /tenant/{tid}/oauth2/v2.0/.well-known/openid-configuration
    if "openid-configuration" in path and method == "GET":
        return _openid_config(path)

    return 404, {"Content-Type": "application/json"}, json.dumps({
        "error": "invalid_request", "error_description": "Endpoint not found"
    }).encode()


def _extract_tenant_id(path: str) -> str:
    parts = path.strip("/").split("/")
    for i, p in enumerate(parts):
        if p == "tenant" and i + 1 < len(parts):
            return parts[i + 1]
    return AZURE_TENANT_ID


def _issue_token(body: bytes, path: str, headers: dict, query_params: dict) -> tuple:
    """Issue OAuth 2.0 token (client_credentials flow)."""
    # Parse form data
    form = {}
    if body:
        for part in body.decode("utf-8", errors="replace").split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                form[k] = v

    tenant_id = _extract_tenant_id(path)
    client_id = form.get("client_id", AZURE_CLIENT_ID)
    scope = form.get("scope", "https://management.azure.com/.default")
    grant_type = form.get("grant_type", "client_credentials")

    token = issue_token(tenant_id, client_id, scope)
    if not token:
        return 401, {
            "Content-Type": "application/json",
            "x-ms-request-id": new_uuid(),
        }, json.dumps({
            "error": "invalid_client",
            "error_description": "Invalid client_id or client_secret",
        }).encode()

    _tokens_issued.append(token)

    return 200, {
        "Content-Type": "application/json",
        "x-ms-request-id": new_uuid(),
    }, json.dumps(token).encode()


def _openid_config(path: str) -> tuple:
    tenant_id = _extract_tenant_id(path)
    return 200, {"Content-Type": "application/json"}, json.dumps({
        "issuer": f"https://sts.windows.net/{tenant_id}/",
        "authorization_endpoint": f"http://localhost:4566/tenant/{tenant_id}/oauth2/v2.0/authorize",
        "token_endpoint": f"http://localhost:4566/tenant/{tenant_id}/oauth2/v2.0/token",
        "jwks_uri": f"http://localhost:4566/tenant/{tenant_id}/discovery/v2.0/keys",
        "response_types_supported": ["code", "id_token", "token"],
        "subject_types_supported": ["pairwise"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "scopes_supported": ["openid", "profile", "email"],
    }).encode()


def _jwks(path: str) -> tuple:
    tenant_id = _extract_tenant_id(path)
    return 200, {"Content-Type": "application/json"}, json.dumps({
        "keys": [{
            "kty": "RSA",
            "use": "sig",
            "kid": f"emulated-key-{tenant_id}",
            "n": "emulated-modulus",
            "e": "AQAB",
        }]
    }).encode()


def reset():
    """Reset Entra ID state."""
    _tokens_issued.clear()
