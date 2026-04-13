"""
MiniStack — Local AWS Service Emulator.
Single-port ASGI application on port 4566 (configurable via GATEWAY_PORT).
Routes requests to service handlers based on AWS headers, paths, and query parameters.
Compatible with AWS CLI, boto3, and any AWS SDK via --endpoint-url.
"""

import argparse
import asyncio
import base64
import json
import logging
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import uuid
from urllib.parse import parse_qs, urlparse

_MINISTACK_HOST = os.environ.get("MINISTACK_HOST", "localhost")
_MINISTACK_PORT = os.environ.get("GATEWAY_PORT", "4566")

# Matches host headers like "{apiId}.execute-api.<host>" or "{apiId}.execute-api.<host>:4566"
_EXECUTE_API_RE = re.compile(
    r"^([a-f0-9]{8})\.execute-api\." + re.escape(_MINISTACK_HOST) + r"(?::\d+)?$"
)
# Matches virtual-hosted S3:
#   "{bucket}.<host>" or "{bucket}.<host>:4566"          (boto3/SDK default)
#   "{bucket}.s3.<host>" or "{bucket}.s3.<host>:4566"    (Terraform AWS provider v4+)
# Does NOT match execute-api, alb, or other sub-service hostnames.
_S3_VHOST_RE = re.compile(
    r"^([^.]+)(?:\.s3)?\." + re.escape(_MINISTACK_HOST) + r"(?::\d+)?$"
)
_S3_VHOST_EXCLUDE_RE = re.compile(r"\.(execute-api|alb|emr|efs|elasticache|s3-control)\.")

from ministack.core.persistence import PERSIST_STATE, load_state, save_all
from ministack.core.responses import set_request_account_id
from ministack.core.router import detect_service, extract_access_key_id, extract_account_id, extract_region
from ministack.services import (
    acm,
    alb,
    apigateway,
    autoscaling,
    apigateway_v1,
    appsync,
    athena,
    cloudformation,
    cloudwatch,
    cloudwatch_logs,
    cognito,
    dynamodb,
    ec2,
    ecr,
    ecs,
    efs,
    elasticache,
    emr,
    eventbridge,
    firehose,
    glue,
    kinesis,
    kms,
    lambda_svc,
    rds,
    rds_data,
    route53,
    s3,
    secretsmanager,
    ses,
    ses_v2,
    sns,
    sqs,
    ssm,
    stepfunctions,
    waf,
    cloudfront,
    servicediscovery,
    s3files,
    codebuild,
)
from ministack.services import iam_sts
from ministack.services.iam_sts import handle_iam_request, handle_sts_request

# ---------------------------------------------------------------------------
# Huawei Cloud service imports (subdirectory)
# ---------------------------------------------------------------------------
from ministack.core.router import HUAWEI_MODE, CLOUD_MODE
from ministack.services.huawei import (
    obs as hw_obs,
    iam_hw,
    smn as hw_smn,
    functiongraph as hw_functiongraph,
    rds_hw as hw_rds,
    dcs as hw_dcs,
    lts as hw_lts,
    vpc_hw as hw_vpc,
    dms as hw_dms,
    aom as hw_aom,
    ecs_hw as hw_ecs,
    apig as hw_apig,
    dis as hw_dis,
    kms_hw as hw_kms,
    csms as hw_csms,
    cce as hw_cce,
    rfs as hw_rfs,
)

# ---------------------------------------------------------------------------
# GCP service imports
# ---------------------------------------------------------------------------
from ministack.core.router import HUAWEI_MODE, CLOUD_MODE, AZURE_MODE
from ministack.services.gcp import (
    storage as gcp_storage,
    pubsub as gcp_pubsub,
    functions as gcp_functions,
    bigquery as gcp_bigquery,
    sql as gcp_sql,
    run as gcp_run,
    logging as gcp_logging,
    monitoring as gcp_monitoring,
    secretmanager as gcp_secretmanager,
    kms as gcp_kms,
    compute as gcp_compute,
    artifactregistry as gcp_artifactregistry,
    metadata as gcp_metadata,
    iam as gcp_iam,
)
from ministack.services.gcp.gcp_services import reset_all as reset_gcp_all

# ---------------------------------------------------------------------------
# Azure Cloud service imports
# ---------------------------------------------------------------------------
from ministack.services.azure import (
    blob_storage,
    entra_id,
    service_bus,
    functions as azure_functions,
    cosmos_db,
    keyvault_secrets,
    keyvault_keys,
    keyvault_certs,
    azure_sql,
    cache_redis,
    monitor_logs,
    monitor_metrics,
    event_hubs,
    event_grid,
    virtual_machines,
    container_instances,
    container_registry,
    arm_deployments,
    cdn_frontdoor,
    logic_apps,
    aad_b2c,
    data_factory,
    synapse,
    communication_email,
    dns,
    load_balancer,
    app_configuration,
    stream_analytics,
    storage_queue,
    api_management,
)

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ministack")

SERVICE_HANDLERS = {
    "s3": s3.handle_request,
    "sqs": sqs.handle_request,
    "cloudformation": cloudformation.handle_request,
    "sns": sns.handle_request,
    "dynamodb": dynamodb.handle_request,
    "lambda": lambda_svc.handle_request,
    "iam": handle_iam_request,
    "sts": handle_sts_request,
    "secretsmanager": secretsmanager.handle_request,
    "logs": cloudwatch_logs.handle_request,
    "ssm": ssm.handle_request,
    "events": eventbridge.handle_request,
    "kinesis": kinesis.handle_request,
    "monitoring": cloudwatch.handle_request,
    "ses": ses.handle_request,
    "acm": acm.handle_request,
    "wafv2": waf.handle_request,
    "states": stepfunctions.handle_request,
    "ecr": ecr.handle_request,
    "ecs": ecs.handle_request,
    "rds": rds.handle_request,
    "elasticache": elasticache.handle_request,
    "glue": glue.handle_request,
    "athena": athena.handle_request,
    "apigateway": apigateway.handle_request,
    "firehose": firehose.handle_request,
    "route53": route53.handle_request,
    "cognito-idp": cognito.handle_request,
    "cognito-identity": cognito.handle_request,
    "ec2": ec2.handle_request,
    "elasticmapreduce": emr.handle_request,
    "elasticloadbalancing": alb.handle_request,
    "elasticfilesystem": efs.handle_request,
    "kms": kms.handle_request,
    "cloudfront": cloudfront.handle_request,
    "codebuild": codebuild.handle_request,
    "appsync": appsync.handle_request,
    "servicediscovery": servicediscovery.handle_request,
    "s3files": s3files.handle_request,
    "rds-data": rds_data.handle_request,
    "autoscaling": autoscaling.handle_request,
    # ------------------------------------------------------------------
    # Huawei Cloud service handlers
    # ------------------------------------------------------------------
    "obs": hw_obs.handle_request,
    "iam_hw": iam_hw.handle_request,
    "smn": hw_smn.handle_request,
    "functiongraph": hw_functiongraph.handle_request,
    "rds_hw": hw_rds.handle_request,
    "dcs": hw_dcs.handle_request,
    "lts": hw_lts.handle_request,
    "vpc_hw": hw_vpc.handle_request,
    "dms": hw_dms.handle_request,
    "aom": hw_aom.handle_request,
    "ecs_hw": hw_ecs.handle_request,
    "apig": hw_apig.handle_request,
    "dis": hw_dis.handle_request,
    "kms_hw": hw_kms.handle_request,
    "csms": hw_csms.handle_request,
    "cce": hw_cce.handle_request,
    "rfs": hw_rfs.handle_request,
    # ------------------------------------------------------------------
    # Azure Cloud service handlers
    # ------------------------------------------------------------------
    "azure_blob": blob_storage.handle_request,
    "entra_id": entra_id.handle_request,
    "azure_service_bus": service_bus.handle_request,
    "azure_functions": azure_functions.handle_request,
    "azure_cosmos": cosmos_db.handle_request,
    "azure_kv_secrets": keyvault_secrets.handle_request,
    "azure_kv_keys": keyvault_keys.handle_request,
    "azure_kv_certs": keyvault_certs.handle_request,
    "azure_sql": azure_sql.handle_request,
    "azure_cache_redis": cache_redis.handle_request,
    "azure_monitor_logs": monitor_logs.handle_request,
    "azure_monitor_metrics": monitor_metrics.handle_request,
    "azure_event_hubs": event_hubs.handle_request,
    "azure_event_grid": event_grid.handle_request,
    "azure_virtual_machines": virtual_machines.handle_request,
    "azure_container_instances": container_instances.handle_request,
    "azure_container_registry": container_registry.handle_request,
    "azure_arm": arm_deployments.handle_request,
    "azure_cdn": cdn_frontdoor.handle_request,
    "azure_logic_apps": logic_apps.handle_request,
    "azure_aad_b2c": aad_b2c.handle_request,
    "azure_data_factory": data_factory.handle_request,
    "azure_synapse": synapse.handle_request,
    "azure_communication_email": communication_email.handle_request,
    "azure_dns": dns.handle_request,
    "azure_load_balancer": load_balancer.handle_request,
    "azure_app_configuration": app_configuration.handle_request,
    "azure_stream_analytics": stream_analytics.handle_request,
    "azure_storage_queue": storage_queue.handle_request,
    "azure_api_management": api_management.handle_request,
    # ------------------------------------------------------------------
    # GCP service handlers
    # ------------------------------------------------------------------
    "gcp_storage": gcp_storage.handle_request,
    "gcp_pubsub": gcp_pubsub.handle_request,
    "gcp_functions": gcp_functions.handle_request,
    "gcp_bigquery": gcp_bigquery.handle_request,
    "gcp_sql": gcp_sql.handle_request,
    "gcp_run": gcp_run.handle_request,
    "gcp_logging": gcp_logging.handle_request,
    "gcp_monitoring": gcp_monitoring.handle_request,
    "gcp_secretmanager": gcp_secretmanager.handle_request,
    "gcp_kms": gcp_kms.handle_request,
    "gcp_compute": gcp_compute.handle_request,
    "gcp_artifactregistry": gcp_artifactregistry.handle_request,
    "gcp_metadata": gcp_metadata.handle_request,
    "gcp_iam": gcp_iam.handle_request,
}

SERVICE_NAME_ALIASES = {
    "cloudwatch-logs": "logs",
    "cloudwatch": "monitoring",
    "eventbridge": "events",
    "step-functions": "states",
    "stepfunctions": "states",
    "execute-api": "apigateway",
    "apigatewayv2": "apigateway",
    "kinesis-firehose": "firehose",
    "route53": "route53",
    "cognito-idp": "cognito-idp",
    "cognito-identity": "cognito-identity",
    "elbv2": "elasticloadbalancing",
    "elb": "elasticloadbalancing",
    "ecr": "ecr",
    "rds-data": "rds-data",
}


def _resolve_port():
    """Resolve gateway port: GATEWAY_PORT > EDGE_PORT > 4566."""
    return os.environ.get("GATEWAY_PORT") or os.environ.get("EDGE_PORT") or "4566"


if os.environ.get("LOCALSTACK_PERSISTENCE") == "1" and os.environ.get("S3_PERSIST") != "1":
    os.environ["S3_PERSIST"] = "1"
    logger.info("LOCALSTACK_PERSISTENCE=1 detected — enabling S3_PERSIST")

_services_env = os.environ.get("SERVICES", "").strip()
if _services_env:
    _requested = {s.strip() for s in _services_env.split(",") if s.strip()}
    _resolved = set()
    for _name in _requested:
        _key = SERVICE_NAME_ALIASES.get(_name, _name)
        if _key in SERVICE_HANDLERS:
            _resolved.add(_key)
        else:
            logger.warning("SERVICES: unknown service '%s' (resolved as '%s') — skipping", _name, _key)
    SERVICE_HANDLERS = {k: v for k, v in SERVICE_HANDLERS.items() if k in _resolved}
    logger.info("SERVICES filter active — enabled: %s", sorted(SERVICE_HANDLERS.keys()))

BANNER = r"""
  __  __ _       _ ____  _             _
 |  \/  (_)_ __ (_) ___|| |_ __ _  ___| | __
 | |\/| | | '_ \| \___ \| __/ _` |/ __| |/ /
 | |  | | | | | | |___) | || (_| | (__|   <
 |_|  |_|_|_| |_|_|____/ \__\__,_|\___|_|\_\

 Local AWS Service Emulator — Port {port}
 Services: S3, SQS, SNS, DynamoDB, Lambda, IAM, STS, SecretsManager, CloudWatch Logs,
          SSM, EventBridge, Kinesis, CloudWatch, SES, SES v2, ACM, WAF v2, Step Functions,
          ECS, RDS, ElastiCache, Glue, Athena, API Gateway, Firehose, Route53,
          Cognito, EC2, EMR, EBS, EFS, ALB/ELBv2, CloudFormation, KMS, ECR, CloudFront,
          AppSync, Cloud Map, S3 Files, RDS Data API, CodeBuild
""" + (f"\n Multi-Cloud Mode: {CLOUD_MODE} — AWS:41  Azure:30  Huawei:17  GCP:14" if CLOUD_MODE != "aws" else "")


async def app(scope, receive, send):
    """ASGI application entry point."""
    if scope["type"] == "lifespan":
        await _handle_lifespan(scope, receive, send)
        return

    if scope["type"] != "http":
        return

    method = scope["method"]
    path = scope["path"]
    query_string = scope.get("query_string", b"").decode("utf-8")
    query_params = parse_qs(query_string, keep_blank_values=True)

    headers = {}
    for name, value in scope.get("headers", []):
        try:
            headers[name.decode("latin-1").lower()] = value.decode("utf-8")
        except UnicodeDecodeError:
            headers[name.decode("latin-1").lower()] = value.decode("latin-1")

    body = b""
    has_body = headers.get("content-length") or headers.get("transfer-encoding")
    if has_body or method in ("POST", "PUT", "PATCH"):
        while True:
            message = await receive()
            body += message.get("body", b"")
            if not message.get("more_body", False):
                break

    # AWS SDK v2 sends PutObject with Transfer-Encoding: chunked and
    # x-amz-content-sha256: STREAMING-AWS4-HMAC-SHA256-PAYLOAD[-TRAILER].
    # Decode the AWS chunked format: each chunk is "<hex>;chunk-signature=...\r\n<data>\r\n"
    # terminated by "0;chunk-signature=...\r\n".
    sha256_header = headers.get("x-amz-content-sha256", "")
    content_encoding = headers.get("content-encoding", "")
    if sha256_header.startswith("STREAMING-") or "aws-chunked" in content_encoding or headers.get("x-amz-decoded-content-length"):
        decoded = b""
        remaining = body
        while remaining:
            crlf = remaining.find(b"\r\n")
            if crlf == -1:
                break
            chunk_header = remaining[:crlf].decode("ascii", errors="replace")
            size_hex = chunk_header.split(";")[0].strip()
            try:
                chunk_size = int(size_hex, 16)
            except ValueError:
                break
            if chunk_size == 0:
                break
            data_start = crlf + 2
            decoded += remaining[data_start:data_start + chunk_size]
            remaining = remaining[data_start + chunk_size + 2:]  # skip trailing \r\n
        if decoded or not body:
            body = decoded
        if "aws-chunked" in content_encoding:
            ce = [p.strip() for p in content_encoding.split(",") if p.strip() != "aws-chunked"]
            if ce:
                headers["content-encoding"] = ", ".join(ce)
            else:
                headers.pop("content-encoding", None)

    request_id = str(uuid.uuid4())

    # Set per-request account ID from credentials (multi-tenancy support).
    # If the access key is a 12-digit number, it becomes the account ID.
    _access_key = extract_access_key_id(headers)
    if _access_key:
        set_request_account_id(_access_key)

    # Lambda layer content download: /_ministack/lambda-layers/{name}/{ver}/content
    if path.startswith("/_ministack/lambda-layers/") and method == "GET":
        lp = path.split("/")  # ['', '_ministack', 'lambda-layers', name, ver, 'content']
        if len(lp) >= 6 and lp[5] == "content" and lp[4].isdigit():
            from ministack.services import lambda_svc
            status, resp_headers, resp_body = lambda_svc.serve_layer_content(lp[3], int(lp[4]))
            await _send_response(send, status, resp_headers, resp_body)
            return

    # Cognito JWKS / OpenID Configuration well-known endpoints
    # Path: /{poolId}/.well-known/jwks.json  or  /{poolId}/.well-known/openid-configuration
    if "/.well-known/" in path and method == "GET":
        if path.endswith("/.well-known/jwks.json"):
            _pool_id = path.rsplit("/.well-known/jwks.json", 1)[0].lstrip("/")
            if _pool_id:
                _region = extract_region(headers) or "us-east-1"
                status, resp_headers, resp_body = cognito.well_known_jwks(_pool_id)
                await _send_response(send, status, resp_headers, resp_body)
                return
        elif path.endswith("/.well-known/openid-configuration"):
            _pool_id = path.rsplit("/.well-known/openid-configuration", 1)[0].lstrip("/")
            if _pool_id:
                _region = extract_region(headers) or "us-east-1"
                status, resp_headers, resp_body = cognito.well_known_openid_configuration(_pool_id, _region)
                await _send_response(send, status, resp_headers, resp_body)
                return

    # Admin endpoints — no wildcard CORS headers (return early, before CORS block)
    if path == "/_ministack/reset" and method == "POST":
        _reset_all_state()
        await _send_response(send, 200, {"Content-Type": "application/json"},
                             json.dumps({"reset": "ok"}).encode())
        return

    if path == "/_ministack/config" and method == "POST":
        _ALLOWED_CONFIG_KEYS = {
            "athena.ATHENA_ENGINE", "athena.ATHENA_DATA_DIR",
            "stepfunctions._sfn_mock_config",
            "lambda_svc.LAMBDA_EXECUTOR",
        }
        try:
            config = json.loads(body) if body else {}
        except json.JSONDecodeError:
            config = {}
        applied = {}
        for key, value in config.items():
            if key not in _ALLOWED_CONFIG_KEYS:
                logger.warning("/_ministack/config: rejected key %s (not in whitelist)", key)
                continue
            if "." in key:
                mod_name, var_name = key.rsplit(".", 1)
                try:
                    mod = __import__(f"ministack.services.{mod_name}", fromlist=[var_name])
                    setattr(mod, var_name, value)
                    applied[key] = value
                except (ImportError, AttributeError) as e:
                    logger.warning("/_ministack/config: failed to set %s: %s", key, e)
        await _send_response(send, 200, {"Content-Type": "application/json"},
                             json.dumps({"applied": applied}).encode())
        return

    # ------------------------------------------------------------------
    # Huawei Cloud admin endpoints
    # ------------------------------------------------------------------
    if path == "/_huawei/health" and method == "GET":
        huawei_services = {
            "obs": "available", "iam_hw": "available", "smn": "available",
            "functiongraph": "available", "rds_hw": "available", "dcs": "available",
            "lts": "available", "vpc_hw": "available", "dms": "available",
            "aom": "available", "ecs_hw": "available", "apig": "available",
            "dis": "available", "kms_hw": "available", "csms": "available",
            "cce": "available", "rfs": "available",
        }
        await _send_response(send, 200, {"Content-Type": "application/json"},
                             json.dumps({"services": huawei_services, "mode": HUAWEI_MODE}).encode())
        return

    if path == "/_huawei/reset" and method == "POST":
        _reset_huawei_state()
        await _send_response(send, 200, {"Content-Type": "application/json"},
                             json.dumps({"reset": "ok", "scope": "huawei"}).encode())
        return

    # ------------------------------------------------------------------
    # Azure Cloud admin endpoints
    # ------------------------------------------------------------------
    if path == "/_azure/health" and method == "GET":
        azure_services = {
            "azure_blob": "available", "entra_id": "available", "azure_service_bus": "available",
            "azure_functions": "available", "azure_cosmos": "available",
            "azure_kv_secrets": "available", "azure_kv_keys": "available", "azure_kv_certs": "available",
            "azure_sql": "available", "azure_cache_redis": "available",
            "azure_monitor_logs": "available", "azure_monitor_metrics": "available",
            "azure_event_hubs": "available", "azure_event_grid": "available",
            "azure_virtual_machines": "available", "azure_container_instances": "available",
            "azure_container_registry": "available", "azure_arm": "available",
            "azure_cdn": "available", "azure_logic_apps": "available", "azure_aad_b2c": "available",
            "azure_data_factory": "available", "azure_synapse": "available",
            "azure_communication_email": "available", "azure_dns": "available",
            "azure_load_balancer": "available", "azure_app_configuration": "available",
            "azure_stream_analytics": "available", "azure_storage_queue": "available",
            "azure_api_management": "available",
        }
        await _send_response(send, 200, {"Content-Type": "application/json"},
                             json.dumps({"services": azure_services, "mode": AZURE_MODE}).encode())
        return

    if path == "/_azure/reset" and method == "POST":
        _reset_azure_state()
        await _send_response(send, 200, {"Content-Type": "application/json"},
                             json.dumps({"reset": "ok", "scope": "azure"}).encode())
        return

    # ------------------------------------------------------------------
    # Multi-cloud consolidated endpoints
    # ------------------------------------------------------------------
    if path == "/_multicloud/health" and method == "GET":
        from ministack.core.router import CLOUD_MODE as _cm
        await _send_response(send, 200, {"Content-Type": "application/json"},
                             json.dumps({
                                 "cloud_mode": _cm,
                                 "aws_services": len([k for k in SERVICE_HANDLERS if not k.startswith("azure_") and k not in ("obs","iam_hw","smn","functiongraph","rds_hw","dcs","lts","vpc_hw","dms","aom","ecs_hw","apig","dis","kms_hw","csms","cce","rfs")]),
                                 "azure_services": len([k for k in SERVICE_HANDLERS if k.startswith("azure_")]),
                                 "huawei_services": len([k for k in SERVICE_HANDLERS if k in ("obs","iam_hw","smn","functiongraph","rds_hw","dcs","lts","vpc_hw","dms","aom","ecs_hw","apig","dis","kms_hw","csms","cce","rfs")]),
                                 "status": "available",
                             }).encode())
        return

    # ------------------------------------------------------------------
    # GCP admin endpoints
    # ------------------------------------------------------------------
    if path == "/_gcp/health" and method == "GET":
        gcp_services = {
            "gcp_storage": "available", "gcp_pubsub": "available", "gcp_functions": "available",
            "gcp_bigquery": "available", "gcp_sql": "available", "gcp_run": "available",
            "gcp_logging": "available", "gcp_monitoring": "available",
            "gcp_secretmanager": "available", "gcp_kms": "available", "gcp_compute": "available",
            "gcp_artifactregistry": "available", "gcp_metadata": "available", "gcp_iam": "available",
        }
        await _send_response(send, 200, {"Content-Type": "application/json"},
                             json.dumps({"services": gcp_services, "mode": CLOUD_MODE}).encode())
        return

    if path == "/_gcp/reset" and method == "POST":
        _reset_gcp_state()
        await _send_response(send, 200, {"Content-Type": "application/json"},
                             json.dumps({"reset": "ok", "scope": "gcp"}).encode())
        return

    # S3 Control API — /v20180820/... with x-amz-account-id header
    if path.startswith("/v20180820/"):
        if path.startswith("/v20180820/tags/"):
            from urllib.parse import unquote
            raw_arn = path[len("/v20180820/tags/"):]
            arn = unquote(raw_arn)
            # ARN format: arn:aws:s3:::bucket-name  or  arn:aws:s3:::bucket-name/object-key
            bucket_name = arn.split(":::")[-1].split("/")[0] if ":::" in arn else arn.split("/")[0]

            if method == "GET":
                # ListTagsForResource — return real tags from s3._bucket_tags
                tags = s3._bucket_tags.get(bucket_name, {})
                tag_members = "".join(
                    f"<member><Key>{k}</Key><Value>{v}</Value></member>"
                    for k, v in tags.items()
                )
                xml_body = (
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    '<ListTagsForResourceResult xmlns="https://awss3control.amazonaws.com/doc/2018-08-20/">'
                    f"<Tags>{tag_members}</Tags>"
                    "</ListTagsForResourceResult>"
                ).encode()
                await _send_response(send, 200, {
                    "Content-Type": "application/xml",
                    "x-amzn-requestid": request_id,
                }, xml_body)
            elif method == "PUT":
                # TagResource — merge tags into s3._bucket_tags
                try:
                    payload = json.loads(body) if body else {}
                    new_tags = {t["Key"]: t["Value"] for t in payload.get("Tags", [])}
                    existing = s3._bucket_tags.get(bucket_name, {})
                    existing.update(new_tags)
                    s3._bucket_tags[bucket_name] = existing
                except Exception as e:
                    logger.warning("S3 Control TagResource parse error: %s", e)
                await _send_response(send, 204, {
                    "x-amzn-requestid": request_id,
                }, b"")
            elif method == "DELETE":
                # UntagResource — remove specified keys
                keys_to_remove = query_params.get("tagKeys", [])
                if isinstance(keys_to_remove, str):
                    keys_to_remove = [keys_to_remove]
                tags = s3._bucket_tags.get(bucket_name, {})
                for k in keys_to_remove:
                    tags.pop(k, None)
                s3._bucket_tags[bucket_name] = tags
                await _send_response(send, 204, {
                    "x-amzn-requestid": request_id,
                }, b"")
            else:
                await _send_response(send, 200, {
                    "Content-Type": "application/json",
                    "x-amzn-requestid": request_id,
                }, b"{}")
        else:
            # All other S3 Control operations — accept silently
            await _send_response(send, 200, {
                "Content-Type": "application/json",
                "x-amzn-requestid": request_id,
            }, b"{}")
        return

    # RDS Data API — /Execute, /BeginTransaction, /CommitTransaction, /RollbackTransaction, /BatchExecute
    if path in ("/Execute", "/BeginTransaction", "/CommitTransaction", "/RollbackTransaction", "/BatchExecute"):
        status, resp_headers, resp_body = await rds_data.handle_request(method, path, headers, body, query_params)
        await _send_response(send, status, resp_headers, resp_body)
        return

    # SES v2 REST API — /v2/email/...
    if path.startswith("/v2/email"):
        status, resp_headers, resp_body = await ses_v2.handle_request(method, path, headers, body, query_params)
        await _send_response(send, status, resp_headers, resp_body)
        return

    if path in ("/_localstack/health", "/health", "/_ministack/health"):
        await _send_response(send, 200, {
            "Content-Type": "application/json",
            "x-amzn-requestid": request_id,
        }, json.dumps({
            "services": {s: "available" for s in SERVICE_HANDLERS},
            "edition": "light",
            "version": "3.0.0.dev",
        }).encode())
        return

    # ------------------------------------------------------------------
    # Dashboard endpoint
    # ------------------------------------------------------------------
    if path in ("/", "/dashboard", "/_ministack/dashboard") and method == "GET":
        import importlib.resources
        try:
            # Python 3.9+ compatible resource reading
            dashboard_html = importlib.resources.files("ministack.static").joinpath("dashboard.html").read_bytes()
        except Exception:
            # Fallback: try direct path
            import os
            dashboard_path = os.path.join(os.path.dirname(__file__), "static", "dashboard.html")
            if os.path.exists(dashboard_path):
                with open(dashboard_path, "rb") as f:
                    dashboard_html = f.read()
            else:
                dashboard_html = b"<h1>Dashboard not found</h1>"
        await _send_response(send, 200, {
            "Content-Type": "text/html; charset=utf-8",
        }, dashboard_html)
        return

    if method == "OPTIONS":
        await _send_response(send, 200, {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, HEAD, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Expose-Headers": "*",
            "Access-Control-Max-Age": "86400",
            "Content-Length": "0",
            "x-amzn-requestid": request_id,
        }, b"")
        return

    # API Gateway execute-api data plane: host = {apiId}.execute-api.localhost[:{port}]
    host = headers.get("host", "")
    _execute_match = _EXECUTE_API_RE.match(host)
    if _execute_match:
        api_id = _execute_match.group(1)
        # Path format: /{stage}/{proxy+}  or just /{proxy+} if stage is $default
        path_parts = path.lstrip("/").split("/", 1)
        stage = path_parts[0] if path_parts else "$default"
        execute_path = "/" + path_parts[1] if len(path_parts) > 1 else "/"
        try:
            if api_id in apigateway_v1._rest_apis:
                status, resp_headers, resp_body = await apigateway_v1.handle_execute(
                    api_id, stage, method, execute_path, headers, body, query_params
                )
            else:
                status, resp_headers, resp_body = await apigateway.handle_execute(
                    api_id, stage, execute_path, method, headers, body, query_params
                )
        except Exception as e:
            logger.exception("Error in execute-api dispatch: %s", e)
            status, resp_headers, resp_body = 500, {"Content-Type": "application/json"}, json.dumps({"message": str(e)}).encode()
        resp_headers.update({
            "Access-Control-Allow-Origin": "*",
            "x-amzn-requestid": request_id,
            "x-amz-request-id": request_id,
        })
        await _send_response(send, status, resp_headers, resp_body)
        return

    # ALB data-plane — two addressing modes:
    #   1. Host header matches a configured ALB DNS name or {lb-name}.alb.localhost
    #   2. Path prefix /_alb/{lb-name}/...  (no DNS config needed for local testing)
    _alb_lb = alb.find_lb_for_host(host)
    if _alb_lb is None and path.startswith("/_alb/"):
        _alb_path_parts = path[6:].split("/", 1)
        _alb_lb = alb._find_lb_by_name(_alb_path_parts[0])
        if _alb_lb:
            path = "/" + _alb_path_parts[1] if len(_alb_path_parts) > 1 else "/"

    if _alb_lb:
        _alb_port = 80
        if ":" in host:
            try:
                _alb_port = int(host.rsplit(":", 1)[-1])
            except ValueError:
                pass
        try:
            status, resp_headers, resp_body = await alb.dispatch_request(
                _alb_lb, method, path, headers, body, query_params, _alb_port
            )
        except Exception as e:
            logger.exception("Error in ALB data-plane dispatch: %s", e)
            status, resp_headers, resp_body = (
                500, {"Content-Type": "application/json"},
                json.dumps({"message": str(e)}).encode(),
            )
        resp_headers.update({
            "Access-Control-Allow-Origin": "*",
            "x-amzn-requestid": request_id,
            "x-amz-request-id": request_id,
        })
        await _send_response(send, status, resp_headers, resp_body)
        return

    # Virtual-hosted S3: {bucket}.localhost[:{port}] — rewrite to path-style and forward to S3
    _s3_vhost = _S3_VHOST_RE.match(host)
    if _s3_vhost and not _execute_match and not _S3_VHOST_EXCLUDE_RE.search(host):
        bucket = _s3_vhost.group(1)
        _non_s3_hosts = {"s3", "s3-control", "sqs", "sns", "dynamodb", "lambda", "iam", "sts",
                         "secretsmanager", "logs", "ssm", "events", "kinesis",
                         "monitoring", "ses", "states", "ecs", "rds", "rds-data", "elasticache",
                         "glue", "athena", "apigateway", "cloudformation", "autoscaling", "codebuild"}
        if bucket not in _non_s3_hosts:
            vhost_path = "/" + bucket + path if path != "/" else "/" + bucket + "/"
            try:
                status, resp_headers, resp_body = await s3.handle_request(
                    method, vhost_path, headers, body, query_params
                )
            except Exception as e:
                logger.exception("Error handling virtual-hosted S3 request: %s", e)
                from xml.sax.saxutils import escape as _xml_esc
                status, resp_headers, resp_body = 500, {"Content-Type": "application/xml"}, (
                    f"<Error><Code>InternalError</Code><Message>{_xml_esc(str(e))}</Message></Error>".encode()
                )
            resp_headers.update({
                "Access-Control-Allow-Origin": "*",
                "x-amzn-requestid": request_id,
                "x-amz-request-id": request_id,
                "x-amz-id-2": base64.b64encode(os.urandom(48)).decode(),
            })
            await _send_response(send, status, resp_headers, resp_body)
            return

    # For unsigned form-encoded requests (e.g. STS AssumeRoleWithWebIdentity),
    # Action is in the body not the query string — merge it in for routing only.
    routing_params = query_params
    if not query_params.get("Action") and headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
        body_params = parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=True)
        if body_params.get("Action"):
            routing_params = {**query_params, "Action": body_params["Action"]}

    service = detect_service(method, path, headers, routing_params)
    region = extract_region(headers)

    logger.debug("%s %s -> service=%s region=%s", method, path, service, region)

    handler = SERVICE_HANDLERS.get(service)
    if not handler:
        await _send_response(send, 400, {"Content-Type": "application/json"},
            json.dumps({"error": f"Unsupported service: {service}"}).encode())
        return

    try:
        status, resp_headers, resp_body = await handler(method, path, headers, body, query_params)
    except Exception as e:
        logger.exception("Error handling %s request: %s", service, e)
        await _send_response(send, 500, {"Content-Type": "application/json"},
            json.dumps({"__type": "InternalError", "message": str(e)}).encode())
        return

    resp_headers.update({
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, HEAD, OPTIONS, PATCH",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Expose-Headers": "*",
        "x-amzn-requestid": request_id,
        "x-amz-request-id": request_id,
        "x-amz-id-2": base64.b64encode(os.urandom(48)).decode(),
    })

    await _send_response(send, status, resp_headers, resp_body)


async def _send_response(send, status, headers, body):
    """Send ASGI HTTP response."""
    def _encode_header_value(v: str) -> bytes:
        try:
            return v.encode("latin-1")
        except UnicodeEncodeError:
            return v.encode("utf-8")

    body_bytes = body if isinstance(body, bytes) else body.encode("utf-8")
    if "content-length" not in {k.lower() for k in headers}:
        headers["Content-Length"] = str(len(body_bytes))
    header_list = [(k.encode("latin-1"), _encode_header_value(str(v))) for k, v in headers.items()]
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": header_list,
    })
    await send({
        "type": "http.response.body",
        "body": body_bytes,
    })


async def _handle_lifespan(scope, receive, send):
    """Handle ASGI lifespan events."""
    while True:
        message = await receive()
        if message["type"] == "lifespan.startup":
            port = _resolve_port()
            logger.info(BANNER.format(port=port))
            _run_init_scripts()
            if PERSIST_STATE:
                _load_persisted_state()
            await send({"type": "lifespan.startup.complete"})
            asyncio.create_task(_run_ready_scripts())
        elif message["type"] == "lifespan.shutdown":
            logger.info("MiniStack shutting down...")
            if PERSIST_STATE:
                save_all({
                    "apigateway": apigateway.get_state,
                    "apigateway_v1": apigateway_v1.get_state,
                    "sqs": sqs.get_state,
                    "sns": sns.get_state,
                    "ssm": ssm.get_state,
                    "secretsmanager": secretsmanager.get_state,
                    "iam": iam_sts.get_state,
                    "dynamodb": dynamodb.get_state,
                    "kms": kms.get_state,
                    "eventbridge": eventbridge.get_state,
                    "cloudwatch_logs": cloudwatch_logs.get_state,
                    "kinesis": kinesis.get_state,
                    "ec2": ec2.get_state,
                    "route53": route53.get_state,
                    "cognito": cognito.get_state,
                    "ecr": ecr.get_state,
                    "cloudwatch": cloudwatch.get_state,
                    "s3": s3.get_state,
                    "lambda": lambda_svc.get_state,
                    "rds": rds.get_state,
                    "ecs": ecs.get_state,
                    "elasticache": elasticache.get_state,
                    "appsync": appsync.get_state,
                    "stepfunctions": stepfunctions.get_state,
                    "alb": alb.get_state,
                    "glue": glue.get_state,
                    "efs": efs.get_state,
                    "waf": waf.get_state,
                    "athena": athena.get_state,
                    "emr": emr.get_state,
                    "cloudfront": cloudfront.get_state,
                    "codebuild": codebuild.get_state,
                    "acm": acm.get_state,
                    "firehose": firehose.get_state,
                    "ses": ses.get_state,
                    "ses_v2": ses_v2.get_state,
                    "servicediscovery": servicediscovery.get_state,
                    "s3files": s3files.get_state,
                    # Huawei Cloud services
                    "obs": obs.get_state,
                    "smn": smn.get_state,
                    "functiongraph": functiongraph.get_state,
                    "rds_hw": rds_hw.get_state,
                    "dcs": dcs.get_state,
                    "lts": lts.get_state,
                })
            _stop_docker_containers()
            await send({"type": "lifespan.shutdown.complete"})
            return


def _stop_docker_containers():
    """Stop all Docker containers managed by MiniStack (RDS, ECS, ElastiCache).
    Uses container labels to find them — does not touch service state."""
    try:
        import docker
        client = docker.from_env()
    except Exception:
        return
    for label in ("ministack=rds", "ministack=ecs", "ministack=elasticache"):
        try:
            for c in client.containers.list(filters={"label": label}):
                try:
                    c.stop(timeout=5)
                    c.remove(v=True)
                except Exception:
                    pass
        except Exception:
            pass


def _load_persisted_state():
    """Load persisted state for services that support it."""
    data = load_state("apigateway")
    if data:
        apigateway.load_persisted_state(data)
        logger.info("Loaded persisted state for apigateway")
    data_v1 = load_state("apigateway_v1")
    if data_v1:
        apigateway_v1.load_persisted_state(data_v1)
        logger.info("Loaded persisted state for apigateway_v1")
    data_sd = load_state("servicediscovery")
    if data_sd:
        servicediscovery.load_persisted_state(data_sd)
        logger.info("Loaded persisted state for servicediscovery")


async def _wait_for_port(port, timeout=30):
    """Wait until the server is accepting TCP connections."""
    import time
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            reader, writer = await asyncio.open_connection('127.0.0.1', port)
            writer.close()
            await writer.wait_closed()
            return
        except OSError:
            await asyncio.sleep(0.1)
    logger.warning('Server did not become ready within %ds — skipping ready.d scripts', timeout)


async def _run_ready_scripts():
    """Execute .sh scripts from /docker-entrypoint-initaws.d/ready.d/ after the server is ready."""
    ready_dir = '/docker-entrypoint-initaws.d/ready.d'
    if not os.path.isdir(ready_dir):
        return
    scripts = sorted(f for f in os.listdir(ready_dir) if f.endswith('.sh'))
    if not scripts:
        return
    port = int(_resolve_port())
    await _wait_for_port(port)
    logger.info('Found %d ready script(s) in %s', len(scripts), ready_dir)
    for script in scripts:
        script_path = os.path.join(ready_dir, script)
        logger.info('Running ready script: %s', script_path)
        try:
            proc = await asyncio.create_subprocess_exec(
                'sh', script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
            if stdout:
                logger.info('  stdout: %s', stdout.decode('utf-8', errors='replace').rstrip())
            if proc.returncode != 0:
                logger.error('Ready script %s failed (exit %d): %s', script_path, proc.returncode,
                             stderr.decode('utf-8', errors='replace'))
            else:
                logger.info('Ready script %s completed successfully', script_path)
        except asyncio.TimeoutError:
            logger.error('Ready script %s timed out after 300s', script_path)
            proc.kill()
        except Exception as e:
            logger.error('Failed to execute ready script %s: %s', script_path, e)


def _run_init_scripts():
    """Execute .sh scripts from /docker-entrypoint-initaws.d/ in alphabetical order."""
    init_dir = "/docker-entrypoint-initaws.d"
    if not os.path.isdir(init_dir):
        return
    scripts = sorted(f for f in os.listdir(init_dir) if f.endswith(".sh"))
    if not scripts:
        return
    logger.info("Found %d init script(s) in %s", len(scripts), init_dir)
    for script in scripts:
        script_path = os.path.join(init_dir, script)
        logger.info("Running init script: %s", script_path)
        try:
            result = subprocess.run(
                ["sh", script_path], env=os.environ,
                capture_output=True, text=True, timeout=300,
            )
            if result.stdout:
                logger.info("  stdout: %s", result.stdout.rstrip())
            if result.returncode != 0:
                logger.error("Init script %s failed (exit %d): %s", script_path, result.returncode, result.stderr)
            else:
                logger.info("Init script %s completed successfully", script_path)
        except subprocess.TimeoutExpired:
            logger.error("Init script %s timed out after 300s", script_path)
        except Exception as e:
            logger.error("Failed to execute init script %s: %s", script_path, e)


def _reset_all_state():
    """Wipe all in-memory state across every service module, and persisted files if enabled."""

    from ministack.core.persistence import PERSIST_STATE, STATE_DIR
    from ministack.services.iam_sts import reset as _iam_reset
    from ministack.services.s3 import DATA_DIR as S3_DATA_DIR
    from ministack.services.s3 import PERSIST as S3_PERSIST

    for mod, fn in [
        (s3, s3.reset), (sqs, sqs.reset), (sns, sns.reset),
        (dynamodb, dynamodb.reset), (lambda_svc, lambda_svc.reset),
        (secretsmanager, secretsmanager.reset), (cloudwatch_logs, cloudwatch_logs.reset),
        (ssm, ssm.reset), (eventbridge, eventbridge.reset), (kinesis, kinesis.reset),
        (cloudwatch, cloudwatch.reset), (ses, ses.reset),
        (stepfunctions, stepfunctions.reset), (ecs, ecs.reset),
        (rds, rds.reset), (elasticache, elasticache.reset),
        (glue, glue.reset), (athena, athena.reset),
        (apigateway, apigateway.reset),
        (apigateway_v1, apigateway_v1.reset),
        (firehose, firehose.reset),
        (route53, route53.reset),
        (cognito, cognito.reset),
        (ec2, ec2.reset),
        (emr, emr.reset),
        (alb, alb.reset),
        (acm, acm.reset),
        (ses_v2, ses_v2.reset),
        (waf, waf.reset),
        (efs, efs.reset),
        (cloudformation, cloudformation.reset),
        (kms, kms.reset),
        (cloudfront, cloudfront.reset),
        (codebuild, codebuild.reset),
        (ecr, ecr.reset),
        (appsync, appsync.reset),
        (servicediscovery, servicediscovery.reset),
        (rds_data, rds_data.reset),
        (s3files, s3files.reset),
    ]:
        try:
            fn()
        except Exception as e:
            logger.warning("reset() failed for %s: %s", mod.__name__, e)
    try:
        _iam_reset()
    except Exception as e:
        logger.warning("reset() failed for iam_sts: %s", e)

    # Wipe persisted files so a subsequent restart doesn't reload old state
    if PERSIST_STATE and os.path.isdir(STATE_DIR):
        for fname in os.listdir(STATE_DIR):
            if fname.endswith(".json"):
                try:
                    os.remove(os.path.join(STATE_DIR, fname))
                except Exception as e:
                    logger.warning("reset: failed to remove %s: %s", fname, e)
        logger.info("Wiped persisted state files in %s", STATE_DIR)

    if S3_PERSIST and os.path.isdir(S3_DATA_DIR):
        for entry in os.listdir(S3_DATA_DIR):
            entry_path = os.path.join(S3_DATA_DIR, entry)
            try:
                if os.path.isdir(entry_path):
                    shutil.rmtree(entry_path)
                else:
                    os.remove(entry_path)
            except Exception as e:
                logger.warning("reset: failed to remove S3 data %s: %s", entry, e)
        logger.info("Wiped S3 persisted data in %s", S3_DATA_DIR)

    logger.info("State reset complete")


def _reset_huawei_state():
    """Wipe all Huawei Cloud service in-memory state."""
    for mod, fn in [
        (hw_obs, hw_obs.reset), (iam_hw, iam_hw.reset), (hw_smn, hw_smn.reset),
        (hw_functiongraph, hw_functiongraph.reset), (hw_rds, hw_rds.reset),
        (hw_dcs, hw_dcs.reset), (hw_lts, hw_lts.reset), (hw_vpc, hw_vpc.reset),
        (hw_dms, hw_dms.reset), (hw_aom, hw_aom.reset), (hw_ecs, hw_ecs.reset),
        (hw_apig, hw_apig.reset), (hw_dis, hw_dis.reset), (hw_kms, hw_kms.reset),
        (hw_csms, hw_csms.reset), (hw_cce, hw_cce.reset), (hw_rfs, hw_rfs.reset),
    ]:
        try:
            fn()
        except Exception as e:
            logger.warning("Huawei reset() failed for %s: %s", mod.__name__, e)
    logger.info("Huawei Cloud state reset")


def _reset_azure_state():
    """Wipe all Azure service in-memory state."""
    for mod, fn in [
        (blob_storage, blob_storage.reset), (entra_id, entra_id.reset),
        (service_bus, service_bus.reset), (azure_functions, azure_functions.reset),
        (cosmos_db, cosmos_db.reset), (keyvault_secrets, keyvault_secrets.reset),
        (keyvault_keys, keyvault_keys.reset), (keyvault_certs, keyvault_certs.reset),
        (azure_sql, azure_sql.reset), (cache_redis, cache_redis.reset),
        (monitor_logs, monitor_logs.reset), (monitor_metrics, monitor_metrics.reset),
        (event_hubs, event_hubs.reset), (event_grid, event_grid.reset),
        (virtual_machines, virtual_machines.reset), (container_instances, container_instances.reset),
        (container_registry, container_registry.reset), (arm_deployments, arm_deployments.reset),
        (cdn_frontdoor, cdn_frontdoor.reset), (logic_apps, logic_apps.reset),
        (aad_b2c, aad_b2c.reset), (data_factory, data_factory.reset),
        (synapse, synapse.reset), (communication_email, communication_email.reset),
        (dns, dns.reset), (load_balancer, load_balancer.reset),
        (app_configuration, app_configuration.reset), (stream_analytics, stream_analytics.reset),
        (storage_queue, storage_queue.reset), (api_management, api_management.reset),
    ]:
        try:
            fn()
        except Exception as e:
            logger.warning("Azure reset() failed for %s: %s", mod.__name__, e)
    logger.info("Azure Cloud state reset")


def _reset_gcp_state():
    """Wipe all GCP service in-memory state."""
    for mod, fn in [
        (gcp_storage, gcp_storage.reset), (gcp_pubsub, gcp_pubsub.reset),
        (gcp_functions, gcp_functions.reset), (gcp_bigquery, gcp_bigquery.reset),
        (gcp_sql, gcp_sql.reset), (gcp_run, gcp_run.reset),
        (gcp_logging, gcp_logging.reset), (gcp_monitoring, gcp_monitoring.reset),
        (gcp_secretmanager, gcp_secretmanager.reset), (gcp_kms, gcp_kms.reset),
        (gcp_compute, gcp_compute.reset), (gcp_artifactregistry, gcp_artifactregistry.reset),
        (gcp_metadata, gcp_metadata.reset), (gcp_iam, gcp_iam.reset),
    ]:
        try:
            fn()
        except Exception as e:
            logger.warning("GCP reset() failed for %s: %s", mod.__name__, e)
    logger.info("GCP state reset")


def _pid_file(port: int) -> str:
    return os.path.join(tempfile.gettempdir(), f"ministack-{port}.pid")


def main():
    import uvicorn

    parser = argparse.ArgumentParser(description="MiniStack — Local AWS Service Emulator")
    parser.add_argument("-d", "--detach", action="store_true", help="Run in the background (detached mode)")
    parser.add_argument("--stop", action="store_true", help="Stop a detached MiniStack server")
    args = parser.parse_args()

    port = int(_resolve_port())

    if args.stop:
        pf = _pid_file(port)
        if not os.path.exists(pf):
            print(f"No MiniStack PID file found for port {port}. Is it running?")
            raise SystemExit(1)
        with open(pf) as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"MiniStack (PID {pid}) on port {port} stopped.")
        except ProcessLookupError:
            print(f"MiniStack (PID {pid}) was not running. Cleaning up PID file.")
        os.remove(pf)
        return

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", port)) == 0:
            print(f"ERROR: Port {port} is already in use. Is MiniStack already running?\n"
                  f"  Stop it with: ministack --stop\n"
                  f"  Or use a different port: GATEWAY_PORT=4567 ministack")
            raise SystemExit(1)

    if args.detach:
        log_file = os.path.join(os.environ.get("TMPDIR", "/tmp"), f"ministack-{port}.log")
        # Keep a reference to the log file handle — Popen inherits the fd so
        # closing it here would break child process logging.  The handle is
        # intentionally kept open for the lifetime of this (short-lived) parent
        # process; the OS reclaims it when the parent exits.
        log_fh = open(log_file, "w")
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "ministack.app:app",
             "--host", "0.0.0.0", "--port", str(port),
             "--log-level", LOG_LEVEL.lower(),
             "--timeout-keep-alive", "75"],
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        pf = _pid_file(port)
        with open(pf, "w") as f:
            f.write(str(proc.pid))
        print(f"MiniStack started in background (PID {proc.pid}) on port {port}.")
        print(f"  Logs: {log_file}")
        print(f"  Stop: ministack --stop")
        return

    # Foreground — write PID file and clean up on exit
    pf = _pid_file(port)
    with open(pf, "w") as f:
        f.write(str(os.getpid()))

    def _cleanup(*_):
        try:
            os.remove(pf)
        except OSError:
            pass

    signal.signal(signal.SIGTERM, lambda *_: (_cleanup(), sys.exit(0)))
    try:
        uvicorn.run("ministack.app:app", host="0.0.0.0", port=port, log_level=LOG_LEVEL.lower(), timeout_keep_alive=75)
    finally:
        _cleanup()


if __name__ == "__main__":
    main()
