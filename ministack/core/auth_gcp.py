"""
GCP Authentication Module.
Supports service account JWT, OAuth2 token, and Application Default Credentials (ADC) emulation.
Compatible with google-auth-library Python.

Environment variables:
    GCP_PROJECT_ID      — Default project ID (default: ministack-emulator)
    GCP_REGION          — Default region (default: us-central1)
    GCP_ZONE            — Default zone (default: us-central1-a)
    GCP_CREDENTIALS     — Path to service account JSON (optional, uses stub if unset)
"""

import base64
import json
import logging
import os
import time
import uuid

logger = logging.getLogger("auth_gcp")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "ministack-emulator")
GCP_REGION = os.environ.get("GCP_REGION", "us-central1")
GCP_ZONE = os.environ.get("GCP_ZONE", "us-central1-a")
GCP_CREDENTIALS = os.environ.get("GCP_CREDENTIALS", "")

# In-memory token store
_tokens: dict = {}

# Valid service accounts registry
_service_accounts: dict = {}


def register_service_account(email: str, project_id: str = None,
                              private_key_id: str = None) -> dict:
    """Register a service account for emulation."""
    project_id = project_id or GCP_PROJECT_ID
    kid = private_key_id or f"key-{uuid.uuid4().hex[:8]}"
    sa = {
        "email": email,
        "project_id": project_id,
        "private_key_id": kid,
        "client_id": f"client-{uuid.uuid4().hex[:12]}",
    }
    _service_accounts[email] = sa
    return sa


# Register default emulated service account
_default_sa = register_service_account(
    f"ministack@{GCP_PROJECT_ID}.iam.gserviceaccount.com",
    GCP_PROJECT_ID,
)


# ---------------------------------------------------------------------------
# JWT Stub Token
# ---------------------------------------------------------------------------

def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _make_stub_jwt(claims: dict) -> str:
    """Create a structurally valid JWT stub (unsigned)."""
    header = {"alg": "RS256", "typ": "JWT", "kid": "emulated-key"}
    header_b64 = _base64url_encode(json.dumps(header).encode())
    payload_b64 = _base64url_encode(json.dumps(claims).encode())
    signature = _base64url_encode(b"\x00" * 256)
    return f"{header_b64}.{payload_b64}.{signature}"


# ---------------------------------------------------------------------------
# OAuth2 Token Endpoint (Metadata Server Emulation)
# ---------------------------------------------------------------------------

async def issue_access_token(service_account_email: str = None,
                              scopes: list = None) -> dict:
    """
    Issue an OAuth2 access token stub.
    Compatible with google.auth.compute_engine.Credentials.
    """
    sa_email = service_account_email or _default_sa["email"]
    scopes = scopes or ["https://www.googleapis.com/auth/cloud-platform"]

    now = int(time.time())
    claims = {
        "iss": sa_email,
        "sub": sa_email,
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now,
        "exp": now + 3600,
        "scope": " ".join(scopes),
        "email": sa_email,
        "email_verified": True,
    }

    access_token = _make_stub_jwt(claims)

    token_info = {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "expires_at": now + 3600,
        "scopes": scopes,
    }

    _tokens[access_token] = {
        "service_account": sa_email,
        "scopes": scopes,
        "expires_at": now + 3600,
        "claims": claims,
    }

    return token_info


async def issue_id_token(audience: str = None) -> dict:
    """Issue an OIDC ID token stub for Cloud Run / Cloud Functions."""
    audience = audience or f"https://{GCP_REGION}-cloud.run.googleapis.com"
    now = int(time.time())
    claims = {
        "iss": "https://accounts.google.com",
        "aud": audience,
        "iat": now,
        "exp": now + 3600,
        "email": _default_sa["email"],
        "email_verified": True,
        "sub": _default_sa["client_id"],
    }
    id_token = _make_stub_jwt(claims)
    return {"id_token": id_token, "expires_in": 3600}


# ---------------------------------------------------------------------------
# Token Validation
# ---------------------------------------------------------------------------

async def validate_token(token: str) -> dict | None:
    """Validate an access token. In dev mode, accepts any Bearer token."""
    if not token:
        return None

    info = _tokens.get(token)
    if info:
        if info["expires_at"] > int(time.time()):
            return info["claims"]
        else:
            del _tokens[token]
            return None

    # Dev mode: accept any non-empty token
    return {
        "email": _default_sa["email"],
        "email_verified": True,
        "project_id": GCP_PROJECT_ID,
    }


# ---------------------------------------------------------------------------
# Metadata Server Endpoints (169.254.169.254)
# ---------------------------------------------------------------------------

def get_metadata_endpoint(path: str) -> tuple:
    """
    Emulate GCP metadata server responses.
    Paths:
        /computeMetadata/v1/project/project-id
        /computeMetadata/v1/instance/service-accounts/default/token
        /computeMetadata/v1/instance/service-accounts/default/email
        /computeMetadata/v1/instance/zone
    """
    if path == "/computeMetadata/v1/project/project-id":
        return 200, {"Content-Type": "text/plain"}, GCP_PROJECT_ID.encode()

    if path == "/computeMetadata/v1/instance/service-accounts/default/email":
        return 200, {"Content-Type": "text/plain"}, _default_sa["email"].encode()

    if path == "/computeMetadata/v1/instance/service-accounts/default/token":
        token = issue_access_token_sync()
        return 200, {"Content-Type": "application/json"}, json.dumps(token).encode()

    if path == "/computeMetadata/v1/instance/zone":
        return 200, {"Content-Type": "text/plain"}, f"projects/{GCP_PROJECT_ID}/zones/{GCP_ZONE}".encode()

    if path == "/computeMetadata/v1/instance/hostname":
        return 200, {"Content-Type": "text/plain"}, f"{GCP_PROJECT_ID}.internal".encode()

    if path == "/computeMetadata/v1/instance/name":
        return 200, {"Content-Type": "text/plain"}, GCP_PROJECT_ID.encode()

    return 404, {"Content-Type": "text/plain"}, b"Not Found"


def issue_access_token_sync(service_account_email: str = None,
                             scopes: list = None) -> dict:
    """Synchronous version for metadata server."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context — return stub directly
            pass
    except RuntimeError:
        pass

    sa_email = service_account_email or _default_sa["email"]
    scopes = scopes or ["https://www.googleapis.com/auth/cloud-platform"]
    now = int(time.time())
    claims = {
        "iss": sa_email, "sub": sa_email,
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now, "exp": now + 3600,
        "scope": " ".join(scopes), "email": sa_email, "email_verified": True,
    }
    access_token = _make_stub_jwt(claims)
    token_info = {
        "access_token": access_token, "token_type": "Bearer",
        "expires_in": 3600, "expires_at": now + 3600,
    }
    _tokens[access_token] = {
        "service_account": sa_email, "scopes": scopes,
        "expires_at": now + 3600, "claims": claims,
    }
    return token_info


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------

def reset():
    """Clear all issued tokens."""
    _tokens.clear()
