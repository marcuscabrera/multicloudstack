"""
Azure Authentication Module.
Supports Bearer token (OAuth 2.0), Shared Key (Storage), and JWT stub tokens.
Compatible with azure-identity SDK (ClientSecretCredential, DefaultAzureCredential).

Environment variables:
    AZURE_TENANT_ID          — Tenant ID (default: 00000000-0000-0000-0000-000000000000)
    AZURE_SUBSCRIPTION_ID    — Subscription ID (default: 00000000-0000-0000-0000-000000000001)
    AZURE_CLIENT_ID          — Service Principal client_id (default: test)
    AZURE_CLIENT_SECRET      — Service Principal client_secret (default: test)
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import time
import uuid

logger = logging.getLogger("auth_azure")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID", "00000000-0000-0000-0000-000000000000")
AZURE_SUBSCRIPTION_ID = os.environ.get("AZURE_SUBSCRIPTION_ID", "00000000-0000-0000-0000-000000000001")
AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "test")
AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "test")
AZURE_LOCATION = os.environ.get("AZURE_LOCATION", "eastus")
AZURE_STORAGE_ACCOUNT = os.environ.get("AZURE_STORAGE_ACCOUNT", "devstoreaccount1")

# In-memory token store: token_string -> token_info
_tokens: dict = {}

# Valid credentials registry
_credentials: dict = {
    AZURE_CLIENT_ID: {
        "secret": AZURE_CLIENT_SECRET,
        "tenant_id": AZURE_TENANT_ID,
        "subscription_id": AZURE_SUBSCRIPTION_ID,
    }
}


def register_credential(client_id: str, client_secret: str, tenant_id: str = None,
                        subscription_id: str = None) -> None:
    """Register a Service Principal credential."""
    _credentials[client_id] = {
        "secret": client_secret,
        "tenant_id": tenant_id or AZURE_TENANT_ID,
        "subscription_id": subscription_id or AZURE_SUBSCRIPTION_ID,
    }
    logger.info("Registered Azure credential for client_id: %s", client_id[:8] + "****")


# ---------------------------------------------------------------------------
# JWT Stub Token (structurally valid base64, not cryptographically signed)
# ---------------------------------------------------------------------------

def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _make_stub_jwt(claims: dict) -> str:
    """Create a structurally valid JWT stub (unsigned, for emulation)."""
    header = {"alg": "RS256", "typ": "JWT"}
    header_b64 = _base64url_encode(json.dumps(header).encode())
    payload_b64 = _base64url_encode(json.dumps(claims).encode())
    # Fake signature (256 bytes of zeros, base64url)
    signature = _base64url_encode(b"\x00" * 256)
    return f"{header_b64}.{payload_b64}.{signature}"


# ---------------------------------------------------------------------------
# OAuth 2.0 Token Endpoint
# ---------------------------------------------------------------------------

async def issue_token(tenant_id: str = None, client_id: str = None,
                      scope: str = "https://management.azure.com/.default") -> dict:
    """
    Issue an OAuth 2.0 Bearer token stub.
    Compatible with azure-identity ClientSecretCredential.
    """
    tenant_id = tenant_id or AZURE_TENANT_ID
    client_id = client_id or AZURE_CLIENT_ID

    if client_id not in _credentials:
        return None

    now = int(time.time())
    token_id = str(uuid.uuid4())

    claims = {
        "aud": scope,
        "iss": f"https://sts.windows.net/{tenant_id}/",
        "iat": now,
        "nbf": now,
        "exp": now + 3600,
        "appid": client_id,
        "oid": f"oid-{client_id}",
        "tid": tenant_id,
        "ver": "1.0",
        "roles": ["Contributor"],
    }

    access_token = _make_stub_jwt(claims)

    token_info = {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "ext_expires_in": 3600,
        "expires_at": now + 3600,
        "resource": scope,
    }

    _tokens[access_token] = {
        "client_id": client_id,
        "tenant_id": tenant_id,
        "scope": scope,
        "expires_at": now + 3600,
        "claims": claims,
    }

    return token_info


# ---------------------------------------------------------------------------
# Bearer Token Validation
# ---------------------------------------------------------------------------

async def validate_bearer_token(token: str) -> dict | None:
    """
    Validate a Bearer token. In emulation mode, accepts any non-empty token
    or validates against issued tokens.
    """
    if not token:
        return None

    # Check issued tokens
    info = _tokens.get(token)
    if info:
        if info["expires_at"] > int(time.time()):
            return info["claims"]
        else:
            del _tokens[token]
            return None

    # Dev mode: accept any Bearer token (permissive for local dev)
    return {"appid": "dev-client", "tid": AZURE_TENANT_ID, "roles": ["Contributor"]}


# ---------------------------------------------------------------------------
# Shared Key Validation (Azure Storage)
# ---------------------------------------------------------------------------

async def validate_shared_key(account: str, signature: str,
                              string_to_sign: str = "") -> bool:
    """
    Validate Azure Storage Shared Key signature.
    In dev mode, always returns True (permissive).
    """
    # Dev mode: accept any SharedKey
    return True


def _compute_shared_key_signature(account: str, storage_key: str,
                                  string_to_sign: str) -> str:
    """Compute HMAC-SHA256 signature for Shared Key auth."""
    key = base64.b64decode(storage_key)
    sig = hmac.new(key, string_to_sign.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(sig).decode("ascii")


# ---------------------------------------------------------------------------
# Extract auth info from request
# ---------------------------------------------------------------------------

def extract_bearer_token(headers: dict) -> str:
    """Extract Bearer token from Authorization header."""
    auth = headers.get("authorization", headers.get("Authorization", ""))
    if auth.startswith("Bearer "):
        return auth[7:]
    return ""


def extract_shared_key_info(headers: dict) -> dict:
    """Extract SharedKey account and signature from Authorization header."""
    auth = headers.get("authorization", headers.get("Authorization", ""))
    if auth.startswith("SharedKey "):
        parts = auth[10:].split(":", 1)
        if len(parts) == 2:
            return {"account": parts[0], "signature": parts[1]}
    return {}


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------

def reset():
    """Clear all issued tokens."""
    _tokens.clear()
