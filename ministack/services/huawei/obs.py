"""
OBS (Object Storage Service) — Huawei Cloud compatible.
Reuses the S3 handler since Huawei OBS is S3-compatible.
Adds Huawei-specific response headers: x-obs-request-id, x-obs-id-2.

Paths: /v1/{bucket}/...  or  /{bucket}/... (S3-compatible)
"""

import logging
import os

from ministack.services import s3 as _s3

logger = logging.getLogger("obs")

REGION = os.environ.get("HUAWEICLOUD_REGION", os.environ.get("MINISTACK_REGION", "cn-north-4"))


async def handle_request(method: str, path: str, headers: dict, body: bytes, query_params: dict) -> tuple:
    """Handle OBS request by delegating to the S3 handler."""
    # Rewrite Huawei paths to S3-compatible paths if needed
    # OBS: /v1/{bucket}/{key}  ->  S3: /{bucket}/{key}
    if path.startswith("/v1/"):
        path = path[3:]  # strip /v1/

    status, resp_headers, resp_body = await _s3.handle_request(method, path, headers, body, query_params)

    # Add Huawei-specific headers
    resp_headers["x-obs-request-id"] = resp_headers.get("x-amzn-requestid", resp_headers.get("x-amz-request-id", ""))
    resp_headers["x-obs-id-2"] = resp_headers.get("x-amz-id-2", "")

    return status, resp_headers, resp_body


def reset():
    """Reset OBS state (delegates to S3 reset)."""
    _s3.reset()


def get_state():
    """Get OBS state (delegates to S3 state)."""
    return _s3.get_state()
