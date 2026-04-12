"""
Azure Blob Storage — Azurite-compatible.
Reuses S3 handler logic (container=bucket, blob=object).
Supports: Create/Delete/List containers, Upload/Download/Delete blobs, List blobs.

Paths:
    /azure/blob/{account}/{container}
    /azure/blob/{account}/{container}/{blob}
Headers: x-ms-request-id, x-ms-version, x-ms-date
"""

import json
import logging
import os
import time
import uuid

from ministack.core.auth_azure import AZURE_STORAGE_ACCOUNT
from ministack.core.responses import new_uuid
from ministack.services import s3 as _s3

logger = logging.getLogger("azure_blob")

# In-memory storage: account -> {containers: {name: {blobs: {name: {data, metadata, created}}}}}
_storage_accounts: dict = {}

AZURE_BLOB_VERSION = "2023-11-03"


async def handle_request(method: str, path: str, headers: dict, body: bytes, query_params: dict) -> tuple:
    """Handle Azure Blob Storage request."""
    # Extract account from path
    path_parts = path.strip("/").split("/")
    # /azure/blob/{account}/... or just /{account}/{container}/...
    if path.startswith("/azure/blob/"):
        path = path[len("/azure/blob/"):]
    elif path.startswith("/azure/blob"):
        path = path[len("/azure/blob"):]

    parts = path.strip("/").split("/")
    if not parts or not parts[0]:
        return _list_accounts()

    account = parts[0]

    # Ensure account exists
    if account not in _storage_accounts:
        _storage_accounts[account] = {"containers": {}}

    acct = _storage_accounts[account]

    if len(parts) == 1:
        # /{account} — List containers
        return _list_containers(acct)

    container = parts[1]
    rest = parts[2:] if len(parts) > 2 else []

    query = {}
    for k, v in query_params.items():
        query[k] = v[0] if isinstance(v, list) else v

    # Container operations
    if not rest:
        if method == "PUT" or (method == "POST" and query.get("restype") == "container"):
            return _create_container(acct, container)
        if method == "DELETE" and query.get("restype") == "container":
            return _delete_container(acct, container)
        if method == "GET" and query.get("restype") == "container":
            if query.get("comp") == "list":
                return _list_blobs(acct, container)
            return _get_container_props(acct, container)
        return _list_containers(acct)

    # Blob operations
    blob_name = "/".join(rest)

    if method == "PUT":
        return _upload_blob(acct, container, blob_name, body, headers)
    if method == "GET":
        return _download_blob(acct, container, blob_name)
    if method == "DELETE":
        return _delete_blob(acct, container, blob_name)
    if method == "HEAD":
        return _get_blob_props(acct, container, blob_name)

    return 404, _azure_headers(), b"{}"


def _azure_headers(extra: dict = None) -> dict:
    h = {
        "Content-Type": "application/json",
        "x-ms-request-id": str(uuid.uuid4()),
        "x-ms-version": AZURE_BLOB_VERSION,
    }
    if extra:
        h.update(extra)
    return h


def _list_accounts() -> tuple:
    return 200, _azure_headers(), json.dumps({
        "accounts": list(_storage_accounts.keys()) or [AZURE_STORAGE_ACCOUNT]
    }).encode()


def _list_containers(acct: dict) -> tuple:
    containers = [
        {"name": name, "metadata": {}}
        for name in acct["containers"]
    ]
    return 200, _azure_headers({"x-ms-container-prefix": ""}), json.dumps({
        "Containers": containers,
        "Prefix": "",
        "Marker": "",
        "MaxResults": 5000,
    }).encode()


def _create_container(acct: dict, name: str) -> tuple:
    if name in acct["containers"]:
        return 409, _azure_headers(), json.dumps({
            "error": {"code": "ContainerAlreadyExists", "message": f"Container '{name}' already exists."}
        }).encode()
    acct["containers"][name] = {"blobs": {}}
    return 201, _azure_headers({"ETag": f'"{new_uuid()}"', "Last-Modified": time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())}), b""


def _delete_container(acct: dict, name: str) -> tuple:
    if name not in acct["containers"]:
        return 404, _azure_headers(), b""
    del acct["containers"][name]
    return 202, _azure_headers(), b""


def _get_container_props(acct: dict, name: str) -> tuple:
    if name not in acct["containers"]:
        return 404, _azure_headers(), b""
    return 200, _azure_headers({"ETag": f'"{new_uuid()}"'}), b""


def _list_blobs(acct: dict, container: str) -> tuple:
    if container not in acct["containers"]:
        return 404, _azure_headers(), json.dumps({
            "error": {"code": "ContainerNotFound"}
        }).encode()

    blobs = []
    for name, blob in acct["containers"][container]["blobs"].items():
        blobs.append({
            "Name": name,
            "Properties": {
                "Content-Length": str(len(blob.get("data", b""))),
                "Content-Type": blob.get("content_type", "application/octet-stream"),
                "Last-Modified": blob.get("created", ""),
                "Etag": f'"{blob.get("etag", new_uuid())}"',
            },
        })
    return 200, _azure_headers(), json.dumps({"Blobs": blobs}).encode()


def _upload_blob(acct: dict, container: str, blob_name: str, body: bytes, headers: dict) -> tuple:
    if container not in acct["containers"]:
        return 404, _azure_headers(), json.dumps({
            "error": {"code": "ContainerNotFound", "message": f"Container '{container}' not found."}
        }).encode()

    etag = new_uuid()
    now = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
    acct["containers"][container]["blobs"][blob_name] = {
        "data": body,
        "content_type": headers.get("x-ms-blob-content-type", headers.get("Content-Type", "application/octet-stream")),
        "created": now,
        "etag": etag,
        "content_length": len(body),
    }

    return 201, _azure_headers({
        "ETag": f'"{etag}"',
        "Last-Modified": now,
        "Content-MD5": "",
        "x-ms-request-server-encrypted": "true",
    }), b""


def _download_blob(acct: dict, container: str, blob_name: str) -> tuple:
    if container not in acct["containers"]:
        return 404, _azure_headers(), b""
    blob = acct["containers"][container]["blobs"].get(blob_name)
    if not blob:
        return 404, _azure_headers(), json.dumps({
            "error": {"code": "BlobNotFound", "message": f"Blob '{blob_name}' not found."}
        }).encode()

    return 200, _azure_headers({
        "ETag": f'"{blob["etag"]}"',
        "Last-Modified": blob["created"],
        "Content-Type": blob.get("content_type", "application/octet-stream"),
        "Content-Length": str(blob["content_length"]),
        "x-ms-blob-type": "BlockBlob",
        "Accept-Ranges": "bytes",
    }), blob["data"]


def _delete_blob(acct: dict, container: str, blob_name: str) -> tuple:
    if container not in acct["containers"]:
        return 404, _azure_headers(), b""
    if blob_name not in acct["containers"][container]["blobs"]:
        return 404, _azure_headers(), b""
    del acct["containers"][container]["blobs"][blob_name]
    return 202, _azure_headers(), b""


def _get_blob_props(acct: dict, container: str, blob_name: str) -> tuple:
    if container not in acct["containers"]:
        return 404, _azure_headers(), b""
    blob = acct["containers"][container]["blobs"].get(blob_name)
    if not blob:
        return 404, _azure_headers(), b""
    return 200, _azure_headers({
        "ETag": f'"{blob["etag"]}"',
        "Last-Modified": blob["created"],
        "Content-Type": blob.get("content_type", "application/octet-stream"),
        "Content-Length": str(blob["content_length"]),
        "x-ms-blob-type": "BlockBlob",
    }), b""


def reset():
    """Reset Blob Storage state."""
    _storage_accounts.clear()


def get_state():
    import copy
    return {"accounts": copy.deepcopy(_storage_accounts)}
