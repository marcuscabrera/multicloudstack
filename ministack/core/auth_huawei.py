"""
Huawei Cloud Authentication Module.
Supports AK/SK (Access Key / Secret Key) HMAC-SHA256 signature validation
and IAM token-based authentication, compatible with huaweicloudsdkcore.

Environment variables:
    HUAWEICLOUD_SDK_AK       — Access Key (default: test)
    HUAWEICLOUD_SDK_SK       — Secret Key (default: test)
    HUAWEICLOUD_PROJECT_ID   — Project ID (default: 0000000000000000)
    HUAWEICLOUD_REGION       — Region (default: cn-north-4)
"""

import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone

logger = logging.getLogger("auth_huawei")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

HUAWEICLOUD_SDK_AK = os.environ.get("HUAWEICLOUD_SDK_AK", "test")
HUAWEICLOUD_SDK_SK = os.environ.get("HUAWEICLOUD_SDK_SK", "test")
HUAWEICLOUD_PROJECT_ID = os.environ.get("HUAWEICLOUD_PROJECT_ID", "0000000000000000")
HUAWEICLOUD_REGION = os.environ.get("HUAWEICLOUD_REGION", "cn-north-4")

# ---------------------------------------------------------------------------
# In-memory token store: token_id -> token_info
# ---------------------------------------------------------------------------
_tokens: dict = {}

# Valid AK/SK registry (extensible for multi-tenant support)
_credentials: dict = {
    HUAWEICLOUD_SDK_AK: {
        "sk": HUAWEICLOUD_SDK_SK,
        "project_id": HUAWEICLOUD_PROJECT_ID,
        "region": HUAWEICLOUD_REGION,
        "user_id": "huawei-emulated-user-001",
        "domain_id": "huawei-emulated-domain-001",
    }
}


def register_credential(ak: str, sk: str, project_id: str, region: str,
                        user_id: str = None, domain_id: str = None) -> None:
    """Register a new AK/SK credential pair."""
    _credentials[ak] = {
        "sk": sk,
        "project_id": project_id,
        "region": region,
        "user_id": user_id or f"huawei-user-{ak}",
        "domain_id": domain_id or "huawei-emulated-domain-001",
    }
    logger.info("Registered credential for AK: %s", ak[:8] + "****")


# ---------------------------------------------------------------------------
# HMAC-SHA256 signature verification
# ---------------------------------------------------------------------------

def _sign_key(secret_key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
    """Derive the signing key following Huawei Cloud signature v4 algorithm."""
    def _hmac(key: bytes, msg: bytes) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    k_date = _hmac(("HW" + secret_key).encode("utf-8"), date_stamp)
    k_region = _hmac(k_date, region_name)
    k_service = _hmac(k_region, service_name)
    k_signing = _hmac(k_service, "hw4_request")
    return k_signing


def verify_signature(method: str, path: str, headers: dict, body: bytes) -> tuple[bool, str]:
    """
    Verify HMAC-SHA256 signature from Huawei SDK requests.

    Expected headers:
        Authorization: Huawei4-HMAC-SHA256 Credential={ak}/{date}/{region}/{service}/hw4_request,
                       SignedHeaders={headers}, Signature={sig}
        X-Sdk-Date: YYYYMMDDTHHMMSSZ
        Host: {service}.{region}.myhuaweicloud.com
    """
    auth_header = headers.get("authorization", "")
    if not auth_header.startswith("Huawei4-HMAC-SHA256"):
        return False, "Missing or invalid Authorization header"

    # Parse authorization header
    try:
        auth_parts = {}
        for part in auth_header.split(" ", 1)[1].split(","):
            if "=" in part:
                key, value = part.split("=", 1)
                auth_parts[key.strip()] = value.strip()

        credential = auth_parts.get("Credential", "")
        signature = auth_parts.get("Signature", "")
        signed_headers = auth_parts.get("SignedHeaders", "")

        if not all([credential, signature, signed_headers]):
            return False, "Missing required fields in Authorization header"

        # Extract AK and date/region/service from credential
        cred_parts = credential.split("/")
        if len(cred_parts) < 5:
            return False, "Invalid Credential format"

        ak = cred_parts[0]
        date_stamp = cred_parts[1]
        region_name = cred_parts[2]
        service_name = cred_parts[3]

        # Look up credentials
        if ak not in _credentials:
            return False, f"Invalid Access Key: {ak[:8]}****"

        secret_key = _credentials[ak]["sk"]

        # Build string to sign
        sdk_date = headers.get("x-sdk-date", headers.get("X-Sdk-Date", ""))
        if not sdk_date:
            return False, "Missing X-Sdk-Date header"

        host = headers.get("host", "")

        # Create canonical request
        canonical_uri = path.split("?")[0]
        canonical_querystring = ""
        if "?" in path:
            qs = path.split("?", 1)[1]
            # Sort query parameters
            params = sorted([p.split("=", 1) for p in qs.split("&") if p])
            canonical_querystring = "&".join(f"{p[0]}={p[1] if len(p) > 1 else ''}" for p in params)

        signed_header_list = signed_headers.split(";")
        canonical_headers = ""
        for h in sorted(signed_header_list):
            h_lower = h.lower()
            h_value = headers.get(h_lower, "")
            canonical_headers += f"{h_lower}:{h_value}\n"

        payload_hash = hashlib.sha256(body).hexdigest()

        canonical_request = (
            f"{method.upper()}\n"
            f"{canonical_uri}\n"
            f"{canonical_querystring}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{payload_hash}"
        )

        # Create string to sign
        credential_scope = f"{date_stamp}/{region_name}/{service_name}/hw4_request"
        string_to_sign = (
            f"Huawei4-HMAC-SHA256\n"
            f"{sdk_date}\n"
            f"{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        )

        # Calculate signature
        signing_key = _sign_key(secret_key, date_stamp, region_name, service_name)
        calculated_sig = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(calculated_sig, signature):
            return False, "Signature mismatch"

        return True, ak

    except Exception as e:
        logger.error("Signature verification error: %s", e)
        return False, f"Signature verification error: {e}"


# ---------------------------------------------------------------------------
# IAM Token authentication
# ---------------------------------------------------------------------------

def authenticate_token(headers: dict) -> tuple[bool, dict]:
    """
    Validate X-Auth-Token header.
    Returns (valid, token_info) tuple.
    """
    token = headers.get("x-auth-token", headers.get("X-Auth-Token", ""))
    if not token:
        return False, {}

    token_info = _tokens.get(token)
    if not token_info:
        return False, {}

    # Check expiration
    if token_info.get("expires_at", 0) < time.time():
        del _tokens[token]
        return False, {}

    return True, token_info


def create_token(ak: str = None, project_id: str = None,
                 scope: str = "project") -> dict:
    """
    Create an IAM token for the given credentials.
    Returns token dict compatible with Huawei Cloud IAM response format.
    """
    ak = ak or HUAWEICLOUD_SDK_AK
    if ak not in _credentials:
        return None

    cred = _credentials[ak]
    project_id = project_id or cred["project_id"]

    token_id = str(uuid.uuid4()).replace("-", "")
    now = time.time()
    expires_at = now + 86400  # 24 hours

    token_info = {
        "token": {
            "catalog": _build_service_catalog(),
            "expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "issued_at": datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "methods": ["token"],
            "project": {
                "domain": {
                    "id": cred["domain_id"],
                    "name": "huawei-emulated-domain"
                },
                "id": project_id,
                "name": project_id
            },
            "roles": [
                {
                    "id": "huawei-role-admin-001",
                    "name": "admin"
                }
            ],
            "user": {
                "domain": {
                    "id": cred["domain_id"],
                    "name": "huawei-emulated-domain"
                },
                "id": cred["user_id"],
                "name": f"huawei-user-{ak[:8]}"
            }
        },
        "expires_at": token_info["token"]["expires_at"] if "token" in dir() else "",
        "token_id": token_id,
        "expires_at_ts": expires_at,
    }
    token_info["expires_at"] = token_info["token"]["expires_at"]

    _tokens[token_id] = token_info
    return token_info


def _build_service_catalog() -> list:
    """Build a service catalog for the token response."""
    return [
        {
            "endpoints": [
                {
                    "id": f"obs-{HUAWEICLOUD_REGION}-001",
                    "interface": "public",
                    "region": HUAWEICLOUD_REGION,
                    "region_id": HUAWEICLOUD_REGION,
                    "url": f"https://obs.{HUAWEICLOUD_REGION}.myhuaweicloud.com"
                }
            ],
            "id": "obs-001",
            "name": "obs",
            "type": "objectstorage"
        },
        {
            "endpoints": [
                {
                    "id": f"functiongraph-{HUAWEICLOUD_REGION}-001",
                    "interface": "public",
                    "region": HUAWEICLOUD_REGION,
                    "region_id": HUAWEICLOUD_REGION,
                    "url": f"https://functiongraph.{HUAWEICLOUD_REGION}.myhuaweicloud.com"
                }
            ],
            "id": "functiongraph-001",
            "name": "FunctionGraph",
            "type": "functiongraph"
        },
        {
            "endpoints": [
                {
                    "id": f"smn-{HUAWEICLOUD_REGION}-001",
                    "interface": "public",
                    "region": HUAWEICLOUD_REGION,
                    "region_id": HUAWEICLOUD_REGION,
                    "url": f"https://smn.{HUAWEICLOUD_REGION}.myhuaweicloud.com"
                }
            ],
            "id": "smn-001",
            "name": "SMN",
            "type": "smn"
        },
        {
            "endpoints": [
                {
                    "id": f"rds-{HUAWEICLOUD_REGION}-001",
                    "interface": "public",
                    "region": HUAWEICLOUD_REGION,
                    "region_id": HUAWEICLOUD_REGION,
                    "url": f"https://rds.{HUAWEICLOUD_REGION}.myhuaweicloud.com"
                }
            ],
            "id": "rds-001",
            "name": "RDS",
            "type": "rds"
        },
        {
            "endpoints": [
                {
                    "id": f"vpc-{HUAWEICLOUD_REGION}-001",
                    "interface": "public",
                    "region": HUAWEICLOUD_REGION,
                    "region_id": HUAWEICLOUD_REGION,
                    "url": f"https://vpc.{HUAWEICLOUD_REGION}.myhuaweicloud.com"
                }
            ],
            "id": "vpc-001",
            "name": "VPC",
            "type": "network"
        },
        {
            "endpoints": [
                {
                    "id": f"dcs-{HUAWEICLOUD_REGION}-001",
                    "interface": "public",
                    "region": HUAWEICLOUD_REGION,
                    "region_id": HUAWEICLOUD_REGION,
                    "url": f"https://dcs.{HUAWEICLOUD_REGION}.myhuaweicloud.com"
                }
            ],
            "id": "dcs-001",
            "name": "DCS",
            "type": "dcs"
        },
        {
            "endpoints": [
                {
                    "id": f"lts-{HUAWEICLOUD_REGION}-001",
                    "interface": "public",
                    "region": HUAWEICLOUD_REGION,
                    "region_id": HUAWEICLOUD_REGION,
                    "url": f"https://lts.{HUAWEICLOUD_REGION}.myhuaweicloud.com"
                }
            ],
            "id": "lts-001",
            "name": "LTS",
            "type": "lts"
        },
        {
            "endpoints": [
                {
                    "id": f"iam-{HUAWEICLOUD_REGION}-001",
                    "interface": "public",
                    "region": HUAWEICLOUD_REGION,
                    "region_id": HUAWEICLOUD_REGION,
                    "url": f"https://iam.{HUAWEICLOUD_REGION}.myhuaweicloud.com"
                }
            ],
            "id": "iam-001",
            "name": "IAM",
            "type": "iam"
        },
    ]


# ---------------------------------------------------------------------------
# Project/Account extraction
# ---------------------------------------------------------------------------

def extract_project_id(path: str, headers: dict) -> str:
    """
    Extract project_id from URL path or headers.
    Huawei Cloud paths: /v{version}/{project_id}/...
    """
    # Try to extract from path
    parts = path.strip("/").split("/")
    for i, part in enumerate(parts):
        if part.startswith("v") and i + 1 < len(parts):
            # Next segment after version is typically project_id
            candidate = parts[i + 1]
            if candidate and not candidate.startswith("v"):
                return candidate

    # Try headers
    project_id = headers.get("x-project-id", headers.get("X-Project-Id", ""))
    if project_id:
        return project_id

    return HUAWEICLOUD_PROJECT_ID


def extract_region_from_path(path: str, headers: dict) -> str:
    """Extract region from URL path or headers."""
    # Try headers first
    region = headers.get("x-region", headers.get("X-Region", ""))
    if region:
        return region

    # Check path for region patterns
    region_patterns = ["cn-north-", "cn-south-", "cn-east-", "ap-southeast-"]
    for part in path.strip("/").split("/"):
        for prefix in region_patterns:
            if part.startswith(prefix):
                return part

    return HUAWEICLOUD_REGION
