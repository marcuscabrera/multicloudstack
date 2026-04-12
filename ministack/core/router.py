"""
AWS API Request Router.
Routes incoming requests to the correct service handler based on:
  - Authorization header (AWS4-HMAC-SHA256 ... SignedHeaders=host;...)
  - X-Amz-Target header (e.g., DynamoDB_20120810.PutItem)
  - Host header (e.g., sqs.us-east-1.amazonaws.com)
  - URL path patterns (e.g., /2015-03-31/functions for Lambda)

Huawei Cloud support (HUAWEI_MODE=1 or 2):
  - X-Sdk-Date header and Huawei4-HMAC-SHA256 Authorization
  - Path-based routing: /v1/, /v2/, /v3/ prefixes
  - Service detection via path patterns matching Huawei Cloud API structure

Azure Cloud support (AZURE_MODE=1 or 2):
  - Authorization: Bearer or SharedKey headers
  - Path-based routing: /azure/, /tenant/, /keyvault/, /subscriptions/, /api/
  - x-ms-date, x-ms-client-request-id headers
"""

import logging
import os
import re

logger = logging.getLogger("ministack")

# Mode flags: 0=AWS only, 1=platform only, 2=Hybrid
HUAWEI_MODE = os.environ.get("HUAWEI_MODE", "0")
AZURE_MODE = os.environ.get("AZURE_MODE", "0")

# Unified multi-cloud mode: "aws" | "azure" | "huawei" | "gcp" | "all"
CLOUD_MODE = os.environ.get("CLOUD_MODE", "all")


def detect_provider(path: str, headers: dict) -> str:
    """
    Detect which cloud provider a request targets.
    Returns: "aws" | "azure" | "huawei" | "gcp"
    """
    # GCP signals
    gcp_headers = (
        headers.get("x-goog-api-client") or
        headers.get("x-goog-user-project") or
        (headers.get("authorization", "").startswith("Bearer ") and
         "google" in headers.get("authorization", "").lower()) or
        headers.get("x-goog-request-params") or
        headers.get("x-goog-api-key")
    )
    gcp_paths = (
        path.startswith("/storage/v1/") or
        path.startswith("/pubsub/v1/") or
        path.startswith("/cloudfunctions/v") or
        path.startswith("/bigquery/v") or
        path.startswith("/sql/v") or
        path.startswith("/run/v") or
        path.startswith("/logging/v") or
        path.startswith("/computeMetadata/") or
        path.startswith("/v1/projects/") or
        path.startswith("/v1beta1/projects/") or
        path.startswith("/v2/projects/")
    )
    if gcp_headers or gcp_paths:
        if CLOUD_MODE in ("gcp", "all"):
            return "gcp"

    # Azure signals
    azure_headers = (
        headers.get("x-ms-client-request-id") or
        headers.get("x-ms-date") or
        headers.get("x-ms-version") or
        headers.get("authorization", "").startswith("Bearer ") or
        headers.get("authorization", "").startswith("SharedKey ")
    )
    azure_paths = (
        path.startswith("/azure/") or
        path.startswith("/subscriptions/") or
        path.startswith("/tenant/") or
        path.startswith("/keyvault/") or
        path.startswith("/providers/Microsoft.") or
        path.startswith("/api/") or
        "oauth2/v2.0" in path or
        "/.default" in path
    )
    if azure_headers or azure_paths:
        if CLOUD_MODE in ("azure", "all"):
            return "azure"

    # Huawei Cloud signals
    huawei_headers = (
        headers.get("x-auth-token") or
        headers.get("x-sdk-date") or
        "SDK-HMAC-SHA256" in headers.get("authorization", "") or
        "Huawei4-HMAC-SHA256" in headers.get("authorization", "")
    )
    huawei_paths = (
        path.startswith("/v3/auth/") or
        path.startswith("/v1.0/") or
        (path.startswith("/v2/") and not path.startswith("/v2/apis")) or
        path.startswith("/v3/")
    )
    if huawei_headers or huawei_paths:
        if CLOUD_MODE in ("huawei", "all"):
            return "huawei"

    # Default: AWS
    if CLOUD_MODE in ("aws", "all"):
        return "aws"

    # If CLOUD_MODE restricts, return the active mode
    if CLOUD_MODE == "azure":
        return "azure"
    if CLOUD_MODE == "huawei":
        return "huawei"

    return "aws"

# Service detection patterns
SERVICE_PATTERNS = {
    "s3": {
        "host_patterns": [r"s3[\.\-]", r"\.s3\."],
        "path_patterns": [r"^/(?!2\d{3}-)"],  # S3 is the fallback for non-API paths
    },
    "sqs": {
        "host_patterns": [r"sqs\."],
        "target_prefixes": ["AmazonSQS"],
        "path_patterns": [r"/queue/", r"Action="],
    },
    "sns": {
        "host_patterns": [r"sns\."],
        "target_prefixes": ["AmazonSNS"],
    },
    "dynamodb": {
        "target_prefixes": ["DynamoDB_20120810"],
        "host_patterns": [r"dynamodb\."],
    },
    "lambda": {
        "path_patterns": [r"^/2015-03-31/", r"^/2018-10-31/layers"],
        "host_patterns": [r"lambda\."],
    },
    "iam": {
        "host_patterns": [r"iam\."],
        "path_patterns": [r"Action=.*(CreateRole|GetRole|ListRoles|PutRolePolicy)"],
    },
    "sts": {
        "host_patterns": [r"sts\."],
        "target_prefixes": ["AWSSecurityTokenService"],
    },
    "secretsmanager": {
        "target_prefixes": ["secretsmanager"],
        "host_patterns": [r"secretsmanager\."],
    },
    "monitoring": {
        "host_patterns": [r"monitoring\."],
        "target_prefixes": ["GraniteServiceVersion20100801"],
    },
    "logs": {
        "target_prefixes": ["Logs_20140328"],
        "host_patterns": [r"logs\."],
    },
    "ssm": {
        "target_prefixes": ["AmazonSSM"],
        "host_patterns": [r"ssm\."],
    },
    "events": {
        "target_prefixes": ["AmazonEventBridge", "AWSEvents"],
        "host_patterns": [r"events\."],
    },
    "kinesis": {
        "target_prefixes": ["Kinesis_20131202"],
        "host_patterns": [r"kinesis\."],
    },
    "ses": {
        "host_patterns": [r"email\."],
        "path_patterns": [r"Action=Send"],
    },
    "states": {
        "target_prefixes": ["AWSStepFunctions"],
        "host_patterns": [r"states\."],
    },
    "ecs": {
        "target_prefixes": ["AmazonEC2ContainerServiceV20141113"],
        "host_patterns": [r"ecs\."],
        "path_patterns": [r"^/clusters", r"^/taskdefinitions", r"^/tasks", r"^/services", r"^/stoptask"],
    },
    "rds": {
        "host_patterns": [r"rds\."],
        "path_patterns": [r"Action=.*DB"],
    },
    "elasticache": {
        "host_patterns": [r"elasticache\."],
        "path_patterns": [r"Action=.*Cache"],
    },
    "glue": {
        "target_prefixes": ["AWSGlue"],
        "host_patterns": [r"glue\."],
    },
    "athena": {
        "target_prefixes": ["AmazonAthena"],
        "host_patterns": [r"athena\."],
    },
    "firehose": {
        "target_prefixes": ["Firehose_20150804"],
        "host_patterns": [r"firehose\.", r"kinesis-firehose\."],
    },
    "apigateway": {
        "host_patterns": [r"apigateway\.", r"execute-api\."],
        "path_patterns": [r"^/v2/apis"],
    },
    "route53": {
        "host_patterns": [r"route53\."],
        "path_patterns": [r"^/2013-04-01/"],
    },
    "cognito-idp": {
        "target_prefixes": ["AWSCognitoIdentityProviderService"],
        "host_patterns": [r"cognito-idp\."],
    },
    "cognito-identity": {
        "target_prefixes": ["AWSCognitoIdentityService"],
        "host_patterns": [r"cognito-identity\."],
    },
    "elasticmapreduce": {
        "target_prefixes": ["ElasticMapReduce"],
        "host_patterns": [r"elasticmapreduce\."],
    },
    "elasticfilesystem": {
        "host_patterns": [r"elasticfilesystem\."],
        "path_prefixes": ["/2015-02-01/"],
        "credential_scope": "elasticfilesystem",
    },
    "ecr": {
        "target_prefixes": ["AmazonEC2ContainerRegistry_V20150921"],
        "host_patterns": [r"api\.ecr\.", r"ecr\."],
        "credential_scope": "ecr",
    },
    "ec2": {
        "host_patterns": [r"ec2\."],
        "path_patterns": [r"Action=.*Instance", r"Action=.*Security", r"Action=.*KeyPair",
                          r"Action=.*Vpc", r"Action=.*Subnet", r"Action=.*Address",
                          r"Action=.*Image", r"Action=.*Tag", r"Action=.*InternetGateway",
                          r"Action=.*AvailabilityZone"],
    },
    "elasticloadbalancing": {
        "host_patterns": [r"elasticloadbalancing\."],
    },
    "acm": {
        "target_prefixes": ["CertificateManager"],
        "host_patterns": [r"acm\."],
        "credential_scope": "acm",
    },
    "wafv2": {
        "target_prefixes": ["AWSWAF_20190729"],
        "host_patterns": [r"wafv2\."],
        "credential_scope": "wafv2",
    },
    "cloudformation": {
        "host_patterns": [r"cloudformation\."],
    },
    "kms": {
        "target_prefixes": ["TrentService"],
        "host_patterns": [r"kms\."]
    },
    "cloudfront": {
        "host_patterns": [r"cloudfront\."],
        "credential_scope": "cloudfront",
    },
    "codebuild": {
        "target_prefixes": ["CodeBuild_20161006"],
        "host_patterns": [r"codebuild\."],
        "credential_scope": "codebuild",
    },
    "appsync": {
        "host_patterns": [r"appsync\."],
        "path_prefixes": ["/v1/apis", "/v1/tags"],
        "credential_scope": "appsync",
    },
    "servicediscovery": {
        "target_prefixes": ["Route53AutoNaming_v20170314"],
        "host_patterns": [r"servicediscovery\."],
        "credential_scope": "servicediscovery",
    },
    "s3files": {
        "host_patterns": [r"s3files\."],
        "credential_scope": "s3files",
        "path_prefixes": ["/file-systems", "/mount-targets", "/access-points"],
    },
    "rds-data": {
        "host_patterns": [r"rds-data\."],
        "credential_scope": "rds-data",
    },
    "autoscaling": {
        "host_patterns": [r"autoscaling\."],
        "credential_scope": "autoscaling",
    },
}

# ---------------------------------------------------------------------------
# Huawei Cloud service detection patterns
# ---------------------------------------------------------------------------

HUAWEI_SERVICE_PATTERNS = {
    "obs": {
        "path_prefixes": ["/v1/", "/obs/"],
        "host_patterns": [r"obs\."],
    },
    "iam_hw": {
        "path_prefixes": ["/v3/auth", "/v3.0/OS-CREDENTIAL", "/v3/users", "/v3/projects"],
        "host_patterns": [r"iam\."],
    },
    "smn": {
        "path_prefixes": ["/v2/", "/smn/"],
        "host_patterns": [r"smn\."],
    },
    "functiongraph": {
        "path_prefixes": ["/v2/", "/functiongraph/"],
        "host_patterns": [r"functiongraph\."],
    },
    "rds_hw": {
        "path_prefixes": ["/v3/", "/rds/"],
        "host_patterns": [r"rds\."],
    },
    "dcs": {
        "path_prefixes": ["/v1.0/", "/v2/", "/dcs/"],
        "host_patterns": [r"dcs\."],
    },
    "lts": {
        "path_prefixes": ["/v2/", "/lts/"],
        "host_patterns": [r"lts\."],
    },
    "vpc_hw": {
        "path_prefixes": ["/v1/", "/vpc/"],
        "host_patterns": [r"vpc\."],
    },
    "dms": {
        "path_prefixes": ["/v1.0/", "/v2/", "/dms/"],
        "host_patterns": [r"dms\."],
    },
    "aom": {
        "path_prefixes": ["/v1/", "/aom/"],
        "host_patterns": [r"aom\."],
    },
    "ecs_hw": {
        "path_prefixes": ["/v1/", "/ecs/"],
        "host_patterns": [r"ecs\."],
    },
    "apig": {
        "path_prefixes": ["/v2/", "/apigw/"],
        "host_patterns": [r"apig\."],
    },
    "dis": {
        "path_prefixes": ["/v2/", "/dis/"],
        "host_patterns": [r"dis\."],
    },
    "kms_hw": {
        "path_prefixes": ["/v1.0/", "/kms/"],
        "host_patterns": [r"kms\."],
    },
    "csms": {
        "path_prefixes": ["/v1/", "/csms/"],
        "host_patterns": [r"csms\.", r"dwss\."],
    },
    "cce": {
        "path_prefixes": ["/api/v3/", "/cce/"],
        "host_patterns": [r"cce\."],
    },
    "rfs": {
        "path_prefixes": ["/v1/", "/rfs/"],
        "host_patterns": [r"rfs\."],
    },
}


def _detect_huawei_service(path: str, headers: dict) -> str:
    """Detect Huawei Cloud service from path and headers."""
    path_lower = path.lower()
    host = headers.get("host", "")

    # Check path prefixes first (most reliable for Huawei SDK)
    for svc, patterns in HUAWEI_SERVICE_PATTERNS.items():
        for prefix in patterns.get("path_prefixes", []):
            if path_lower.startswith(prefix.lower()):
                return svc

    # Check host patterns
    for svc, patterns in HUAWEI_SERVICE_PATTERNS.items():
        for hp in patterns.get("host_patterns", []):
            if re.search(hp, host):
                return svc

    # Check for Huawei-specific auth header
    if headers.get("x-sdk-date") or headers.get("X-Sdk-Date"):
        # Default to OBS for unclassified Huawei requests (S3-compatible fallback)
        return "obs"

    return ""


# ---------------------------------------------------------------------------
# Azure Cloud service detection
# ---------------------------------------------------------------------------

AZURE_SERVICE_PATTERNS = {
    "azure_blob": {"path_prefixes": ["/azure/blob", "/azure/blob/"]},
    "azure_cosmos": {"path_prefixes": ["/azure/cosmos"]},
    "azure_functions": {"path_prefixes": ["/api/"]},
    "entra_id": {"path_prefixes": ["/tenant/"]},
    "azure_kv_secrets": {"path_prefixes": ["/keyvault/"], "path_contains": ["/secrets"]},
    "azure_kv_keys": {"path_prefixes": ["/keyvault/"], "path_contains": ["/keys"]},
    "azure_kv_certs": {"path_prefixes": ["/keyvault/"], "path_contains": ["/certificates"]},
    "azure_service_bus": {"path_prefixes": ["/subscriptions/"], "path_contains": ["servicebus", "queues", "topics", "namespaces"]},
    "azure_sql": {"path_prefixes": ["/subscriptions/"], "path_contains": ["Microsoft.Sql", "Microsoft.DBforPostgreSQL", "Microsoft.DBforMySQL", "/servers"]},
    "azure_cache_redis": {"path_prefixes": ["/subscriptions/"], "path_contains": ["Microsoft.Cache", "/redis"]},
    "azure_monitor_logs": {"path_prefixes": ["/subscriptions/"], "path_contains": ["microsoft.insights", "/workspaces", "/query"]},
    "azure_monitor_metrics": {"path_prefixes": ["/subscriptions/"], "path_contains": ["microsoft.insights", "/metrics"]},
    "azure_event_hubs": {"path_prefixes": ["/subscriptions/"], "path_contains": ["eventhubs", "Microsoft.EventHub"]},
    "azure_event_grid": {"path_prefixes": ["/subscriptions/"], "path_contains": ["eventgrid", "Microsoft.EventGrid"]},
    "azure_virtual_machines": {"path_prefixes": ["/subscriptions/"], "path_contains": ["Microsoft.Compute", "virtualMachines"]},
    "azure_container_instances": {"path_prefixes": ["/subscriptions/"], "path_contains": ["Microsoft.ContainerInstance", "containerGroups"]},
    "azure_container_registry": {"path_prefixes": ["/subscriptions/"], "path_contains": ["Microsoft.ContainerRegistry", "registries"]},
    "azure_arm": {"path_prefixes": ["/subscriptions/"], "path_contains": ["deployments", "Microsoft.Resources"]},
    "azure_cdn": {"path_prefixes": ["/subscriptions/"], "path_contains": ["Microsoft.Cdn", "FrontDoor", "profiles"]},
    "azure_logic_apps": {"path_prefixes": ["/subscriptions/"], "path_contains": ["Microsoft.Logic", "workflows"]},
    "azure_aad_b2c": {"path_prefixes": ["/tenant/"], "path_contains": ["oauth2", "b2c"]},
    "azure_data_factory": {"path_prefixes": ["/subscriptions/"], "path_contains": ["Microsoft.DataFactory", "factories"]},
    "azure_synapse": {"path_prefixes": ["/subscriptions/"], "path_contains": ["Microsoft.Synapse", "workspaces"]},
    "azure_communication_email": {"path_prefixes": ["/subscriptions/"], "path_contains": ["Microsoft.Communication", "emails"]},
    "azure_dns": {"path_prefixes": ["/subscriptions/"], "path_contains": ["Microsoft.Network", "dnsZones"]},
    "azure_load_balancer": {"path_prefixes": ["/subscriptions/"], "path_contains": ["Microsoft.Network", "loadBalancers"]},
    "azure_app_configuration": {"path_prefixes": ["/azconfig", "/kv/"]},
    "azure_stream_analytics": {"path_prefixes": ["/subscriptions/"], "path_contains": ["Microsoft.StreamAnalytics", "streamingjobs"]},
    "azure_storage_queue": {"path_prefixes": ["/azure/queue"]},
    "azure_api_management": {"path_prefixes": ["/subscriptions/"], "path_contains": ["Microsoft.ApiManagement", "service"]},
}


def _detect_azure_service(path: str, headers: dict) -> str:
    """Detect Azure Cloud service from path and headers."""
    path_lower = path.lower()

    # Check Azure-specific headers first
    has_azure_headers = (
        headers.get("x-ms-date") or
        headers.get("x-ms-client-request-id") or
        headers.get("x-ms-version") or
        headers.get("authorization", "").startswith("Bearer ") or
        headers.get("authorization", "").startswith("SharedKey ")
    )

    # Check path prefixes
    for svc, patterns in AZURE_SERVICE_PATTERNS.items():
        for prefix in patterns.get("path_prefixes", []):
            if path_lower.startswith(prefix.lower()):
                # If pattern has additional constraints, check them
                if "path_contains" in patterns:
                    if any(c.lower() in path_lower for c in patterns["path_contains"]):
                        return svc
                else:
                    return svc

    # If Azure headers present but no specific service matched, try to infer
    if has_azure_headers:
        if path_lower.startswith("/subscriptions/"):
            return "azure_arm"
        if path_lower.startswith("/azure/blob"):
            return "azure_blob"
        if path_lower.startswith("/azure/cosmos"):
            return "azure_cosmos"
        if path_lower.startswith("/api/"):
            return "azure_functions"

    return ""


# ---------------------------------------------------------------------------
# GCP service detection
# ---------------------------------------------------------------------------

GCP_SERVICE_PATTERNS = {
    "gcp_storage": {"path_prefixes": ["/storage/v1/", "/storage/v1"]},
    "gcp_pubsub": {"path_prefixes": ["/pubsub/v1/", "/pubsub/v1"]},
    "gcp_functions": {"path_prefixes": ["/cloudfunctions/v", "/v1/projects/", "/v2/projects/"]},
    "gcp_bigquery": {"path_prefixes": ["/bigquery/v"]},
    "gcp_sql": {"path_prefixes": ["/sql/v"]},
    "gcp_run": {"path_prefixes": ["/run/v"]},
    "gcp_logging": {"path_prefixes": ["/logging/v"]},
    "gcp_monitoring": {"path_prefixes": ["/monitoring/v"]},
    "gcp_secretmanager": {"path_prefixes": ["/v1/projects/", "/v1beta1/projects/"], "path_contains": ["secrets"]},
    "gcp_kms": {"path_prefixes": ["/v1/projects/"], "path_contains": ["keyRings", "cryptoKeys"]},
    "gcp_compute": {"path_prefixes": ["/compute/v1/"]},
    "gcp_artifactregistry": {"path_prefixes": ["/v1/projects/"], "path_contains": ["repositories"]},
    "gcp_metadata": {"path_prefixes": ["/computeMetadata/"]},
    "gcp_iam": {"path_prefixes": ["/v1/projects/", "/v1beta1/projects/"], "path_contains": ["serviceAccounts"]},
}


def _detect_gcp_service(path: str, headers: dict) -> str:
    """Detect GCP service from path."""
    path_lower = path.lower()

    for svc, patterns in GCP_SERVICE_PATTERNS.items():
        for prefix in patterns.get("path_prefixes", []):
            if path_lower.startswith(prefix.lower()):
                if "path_contains" in patterns:
                    if any(c.lower() in path_lower for c in patterns["path_contains"]):
                        return svc
                else:
                    return svc

    # Default to storage for unclassified GCP requests
    if path_lower.startswith("/v1/"):
        return "gcp_storage"

    return ""


def detect_service(method: str, path: str, headers: dict, query_params: dict) -> str:
    """Detect which AWS, Huawei Cloud, Azure, or GCP service a request is targeting.
    Uses detect_provider() for first-level routing.
    """
    # ── First-level: detect provider ──
    provider = detect_provider(path, headers)

    if provider == "gcp":
        return _detect_gcp_service(path, headers) or "gcp_storage"

    if provider == "azure":
        return _detect_azure_service(path, headers) or "azure_arm"

    if provider == "huawei":
        return _detect_huawei_service(path, headers) or "obs"

    # ── AWS detection (original logic) ──
    host = headers.get("host", "")
    target = headers.get("x-amz-target", "")
    auth = headers.get("authorization", "")
    content_type = headers.get("content-type", "")

    # 1. Check X-Amz-Target header (most reliable for JSON-based services)
    if target:
        for svc, patterns in SERVICE_PATTERNS.items():
            for prefix in patterns.get("target_prefixes", []):
                if target.startswith(prefix):
                    return svc

    # 2. Check Authorization header for service name in credential scope
    if auth:
        match = re.search(r"Credential=[^/]+/[^/]+/[^/]+/([^/]+)/", auth)
        if match:
            svc_name = match.group(1)
            if svc_name in SERVICE_PATTERNS:
                return svc_name
            # Map common credential scope names
            scope_map = {
                "monitoring": "monitoring",
                "execute-api": "apigateway",
                "ses": "ses",
                "states": "states",
                "kinesis": "kinesis",
                "events": "events",
                "ssm": "ssm",
                "ecs": "ecs",
                "rds": "rds",
                "elasticache": "elasticache",
                "glue": "glue",
                "athena": "athena",
                "kinesis-firehose": "firehose",
                "route53": "route53",
                "acm": "acm",
                "wafv2": "wafv2",
                "cognito-idp": "cognito-idp",
                "cognito-identity": "cognito-identity",
                "ecr": "ecr",
                "elasticmapreduce": "elasticmapreduce",
                "elasticloadbalancing": "elasticloadbalancing",
                "elasticfilesystem": "elasticfilesystem",
                "cloudformation": "cloudformation",
                "kms": "kms",
                "cloudfront": "cloudfront",
                "codebuild": "codebuild",
                "appsync": "appsync",
                "servicediscovery": "servicediscovery",
                "s3files": "s3files",
                "rds-data": "rds-data",
                "autoscaling": "autoscaling",
            }
            if svc_name in scope_map:
                return scope_map[svc_name]

    # 3. Check query parameters for Action-based APIs (SQS, SNS, IAM, STS, CloudWatch)
    action = query_params.get("Action", [""])[0] if isinstance(query_params.get("Action"), list) else query_params.get("Action", "")
    if action:
        action_service_map = {
            # SQS actions
            "SendMessage": "sqs", "ReceiveMessage": "sqs", "DeleteMessage": "sqs",
            "CreateQueue": "sqs", "DeleteQueue": "sqs", "ListQueues": "sqs",
            "GetQueueUrl": "sqs", "GetQueueAttributes": "sqs", "SetQueueAttributes": "sqs",
            "PurgeQueue": "sqs", "ChangeMessageVisibility": "sqs",
            "ChangeMessageVisibilityBatch": "sqs",
            "SendMessageBatch": "sqs", "DeleteMessageBatch": "sqs",
            "ListQueueTags": "sqs", "TagQueue": "sqs", "UntagQueue": "sqs",
            # SNS actions
            "Publish": "sns", "Subscribe": "sns", "Unsubscribe": "sns",
            "CreateTopic": "sns", "DeleteTopic": "sns", "ListTopics": "sns",
            "ListSubscriptions": "sns", "ConfirmSubscription": "sns",
            "SetTopicAttributes": "sns", "GetTopicAttributes": "sns",
            "ListSubscriptionsByTopic": "sns",
            "GetSubscriptionAttributes": "sns", "SetSubscriptionAttributes": "sns",
            "PublishBatch": "sns",
            # Note: ListTagsForResource is shared by SNS, RDS, and ElastiCache.
            # Routed via credential scope or host header instead.
            "TagResource": "sns", "UntagResource": "sns",
            "CreatePlatformApplication": "sns", "CreatePlatformEndpoint": "sns",
            # IAM actions
            "CreateRole": "iam", "GetRole": "iam", "ListRoles": "iam",
            "DeleteRole": "iam", "CreateUser": "iam", "GetUser": "iam",
            "ListUsers": "iam", "DeleteUser": "iam",
            "CreatePolicy": "iam", "GetPolicy": "iam", "DeletePolicy": "iam",
            "GetPolicyVersion": "iam", "ListPolicyVersions": "iam",
            "CreatePolicyVersion": "iam", "DeletePolicyVersion": "iam",
            "ListPolicies": "iam",
            "AttachRolePolicy": "iam", "DetachRolePolicy": "iam",
            "ListAttachedRolePolicies": "iam",
            "PutRolePolicy": "iam", "GetRolePolicy": "iam",
            "DeleteRolePolicy": "iam", "ListRolePolicies": "iam",
            "CreateAccessKey": "iam", "ListAccessKeys": "iam", "DeleteAccessKey": "iam",
            "CreateInstanceProfile": "iam", "DeleteInstanceProfile": "iam",
            "GetInstanceProfile": "iam", "AddRoleToInstanceProfile": "iam",
            "RemoveRoleFromInstanceProfile": "iam",
            "ListInstanceProfiles": "iam", "ListInstanceProfilesForRole": "iam",
            "UpdateAssumeRolePolicy": "iam",
            "AttachUserPolicy": "iam", "DetachUserPolicy": "iam",
            "ListAttachedUserPolicies": "iam",
            "TagRole": "iam", "UntagRole": "iam", "ListRoleTags": "iam",
            "TagUser": "iam", "UntagUser": "iam", "ListUserTags": "iam",
            "SimulatePrincipalPolicy": "iam", "SimulateCustomPolicy": "iam",
            # STS actions
            "GetCallerIdentity": "sts", "AssumeRole": "sts",
            "GetSessionToken": "sts", "AssumeRoleWithWebIdentity": "sts",
            "AssumeRoleWithSAML": "sts",
            # CloudWatch actions
            "PutMetricData": "monitoring", "GetMetricData": "monitoring",
            "ListMetrics": "monitoring", "PutMetricAlarm": "monitoring",
            "DescribeAlarms": "monitoring", "DeleteAlarms": "monitoring",
            "GetMetricStatistics": "monitoring", "SetAlarmState": "monitoring",
            "EnableAlarmActions": "monitoring", "DisableAlarmActions": "monitoring",
            "DescribeAlarmsForMetric": "monitoring", "DescribeAlarmHistory": "monitoring",
            "PutCompositeAlarm": "monitoring",
            # SES actions
            "SendEmail": "ses", "SendRawEmail": "ses",
            "VerifyEmailIdentity": "ses", "VerifyEmailAddress": "ses",
            "VerifyDomainIdentity": "ses", "VerifyDomainDkim": "ses",
            "ListIdentities": "ses", "DeleteIdentity": "ses",
            "GetSendQuota": "ses", "GetSendStatistics": "ses",
            "ListVerifiedEmailAddresses": "ses",
            "GetIdentityVerificationAttributes": "ses",
            "GetIdentityDkimAttributes": "ses",
            "SetIdentityNotificationTopic": "ses",
            "SetIdentityFeedbackForwardingEnabled": "ses",
            "CreateConfigurationSet": "ses", "DeleteConfigurationSet": "ses",
            "DescribeConfigurationSet": "ses", "ListConfigurationSets": "ses",
            # Note: GetTemplate is shared by SES and CloudFormation.
            # Routed via credential scope or host header instead.
            "CreateTemplate": "ses",
            "DeleteTemplate": "ses", "ListTemplates": "ses", "UpdateTemplate": "ses",
            "SendTemplatedEmail": "ses", "SendBulkTemplatedEmail": "ses",
            # RDS actions
            "CreateDBInstance": "rds", "DeleteDBInstance": "rds", "DescribeDBInstances": "rds",
            "StartDBInstance": "rds", "StopDBInstance": "rds", "RebootDBInstance": "rds",
            "ModifyDBInstance": "rds", "CreateDBCluster": "rds", "DeleteDBCluster": "rds",
            "ModifyDBCluster": "rds",
            "DescribeDBClusters": "rds", "CreateDBSubnetGroup": "rds", "DescribeDBSubnetGroups": "rds",
            "DeleteDBSubnetGroup": "rds",
            "CreateDBParameterGroup": "rds", "DescribeDBParameterGroups": "rds",
            "DeleteDBParameterGroup": "rds", "DescribeDBParameters": "rds",
            "DescribeDBEngineVersions": "rds",
            "DescribeOrderableDBInstanceOptions": "rds",
            "CreateDBSnapshot": "rds", "DeleteDBSnapshot": "rds", "DescribeDBSnapshots": "rds",
            "CreateDBInstanceReadReplica": "rds", "RestoreDBInstanceFromDBSnapshot": "rds",
            "AddTagsToResource": "rds", "RemoveTagsFromResource": "rds",
            # ElastiCache actions
            "CreateCacheCluster": "elasticache", "DeleteCacheCluster": "elasticache",
            "DescribeCacheClusters": "elasticache", "ModifyCacheCluster": "elasticache",
            "RebootCacheCluster": "elasticache",
            "CreateReplicationGroup": "elasticache", "DeleteReplicationGroup": "elasticache",
            "DescribeReplicationGroups": "elasticache", "ModifyReplicationGroup": "elasticache",
            "CreateCacheSubnetGroup": "elasticache", "DescribeCacheSubnetGroups": "elasticache",
            "DeleteCacheSubnetGroup": "elasticache",
            "CreateCacheParameterGroup": "elasticache", "DescribeCacheParameterGroups": "elasticache",
            "DeleteCacheParameterGroup": "elasticache",
            "DescribeCacheParameters": "elasticache", "ModifyCacheParameterGroup": "elasticache",
            "DescribeCacheEngineVersions": "elasticache",
            "CreateSnapshot": "elasticache", "DeleteSnapshot": "elasticache",
            "DescribeSnapshots": "elasticache",
            "IncreaseReplicaCount": "elasticache", "DecreaseReplicaCount": "elasticache",
            # EC2 actions
            "RunInstances": "ec2", "DescribeInstances": "ec2", "TerminateInstances": "ec2",
            "StopInstances": "ec2", "StartInstances": "ec2", "RebootInstances": "ec2",
            "DescribeImages": "ec2",
            "CreateSecurityGroup": "ec2", "DeleteSecurityGroup": "ec2",
            "DescribeSecurityGroups": "ec2",
            "AuthorizeSecurityGroupIngress": "ec2", "RevokeSecurityGroupIngress": "ec2",
            "AuthorizeSecurityGroupEgress": "ec2", "RevokeSecurityGroupEgress": "ec2",
            "CreateKeyPair": "ec2", "DeleteKeyPair": "ec2", "DescribeKeyPairs": "ec2",
            "ImportKeyPair": "ec2",
            "DescribeVpcs": "ec2", "CreateVpc": "ec2", "DeleteVpc": "ec2",
            "DescribeSubnets": "ec2", "CreateSubnet": "ec2", "DeleteSubnet": "ec2",
            "CreateInternetGateway": "ec2", "DeleteInternetGateway": "ec2",
            "DescribeInternetGateways": "ec2",
            "AttachInternetGateway": "ec2", "DetachInternetGateway": "ec2",
            "DescribeAvailabilityZones": "ec2",
            "AllocateAddress": "ec2", "ReleaseAddress": "ec2",
            "AssociateAddress": "ec2", "DisassociateAddress": "ec2",
            "DescribeAddresses": "ec2",
            "CreateTags": "ec2", "DeleteTags": "ec2", "DescribeTags": "ec2",
            "ModifyVpcAttribute": "ec2", "ModifySubnetAttribute": "ec2",
            "CreateRouteTable": "ec2", "DeleteRouteTable": "ec2", "DescribeRouteTables": "ec2",
            "AssociateRouteTable": "ec2", "DisassociateRouteTable": "ec2",
            "CreateRoute": "ec2", "ReplaceRoute": "ec2", "DeleteRoute": "ec2",
            "CreateNetworkInterface": "ec2", "DeleteNetworkInterface": "ec2",
            "DescribeNetworkInterfaces": "ec2",
            "AttachNetworkInterface": "ec2", "DetachNetworkInterface": "ec2",
            "CreateVpcEndpoint": "ec2", "DeleteVpcEndpoints": "ec2",
            "DescribeVpcEndpoints": "ec2",
            # ELBv2 / ALB actions
            "CreateLoadBalancer": "elasticloadbalancing",
            "DescribeLoadBalancers": "elasticloadbalancing",
            "DeleteLoadBalancer": "elasticloadbalancing",
            "DescribeLoadBalancerAttributes": "elasticloadbalancing",
            "ModifyLoadBalancerAttributes": "elasticloadbalancing",
            "CreateTargetGroup": "elasticloadbalancing",
            "DescribeTargetGroups": "elasticloadbalancing",
            "ModifyTargetGroup": "elasticloadbalancing",
            "DeleteTargetGroup": "elasticloadbalancing",
            "DescribeTargetGroupAttributes": "elasticloadbalancing",
            "ModifyTargetGroupAttributes": "elasticloadbalancing",
            "CreateListener": "elasticloadbalancing",
            "DescribeListeners": "elasticloadbalancing",
            "ModifyListener": "elasticloadbalancing",
            "DeleteListener": "elasticloadbalancing",
            "CreateRule": "elasticloadbalancing",
            "DescribeRules": "elasticloadbalancing",
            "ModifyRule": "elasticloadbalancing",
            "DeleteRule": "elasticloadbalancing",
            "SetRulePriorities": "elasticloadbalancing",
            "RegisterTargets": "elasticloadbalancing",
            "DeregisterTargets": "elasticloadbalancing",
            "DescribeTargetHealth": "elasticloadbalancing",
            "AddTags": "elasticloadbalancing",
            "RemoveTags": "elasticloadbalancing",
            "DescribeTags": "elasticloadbalancing",
            # EBS Volumes
            "CreateVolume": "ec2", "DeleteVolume": "ec2", "DescribeVolumes": "ec2",
            "DescribeVolumeStatus": "ec2", "AttachVolume": "ec2", "DetachVolume": "ec2",
            "ModifyVolume": "ec2", "DescribeVolumesModifications": "ec2",
            "EnableVolumeIO": "ec2", "ModifyVolumeAttribute": "ec2",
            "DescribeVolumeAttribute": "ec2",
            # CloudFormation actions
            "CreateStack": "cloudformation", "DescribeStacks": "cloudformation",
            "UpdateStack": "cloudformation", "DeleteStack": "cloudformation",
            "ListStacks": "cloudformation",
            "DescribeStackEvents": "cloudformation",
            "DescribeStackResource": "cloudformation", "DescribeStackResources": "cloudformation",
            "ListStackResources": "cloudformation",
            "GetTemplateSummary": "cloudformation",
            "ValidateTemplate": "cloudformation",
            "CreateChangeSet": "cloudformation", "DescribeChangeSet": "cloudformation",
            "ExecuteChangeSet": "cloudformation", "DeleteChangeSet": "cloudformation",
            "ListChangeSets": "cloudformation",
            "ListExports": "cloudformation", "ListImports": "cloudformation",
            "UpdateTerminationProtection": "cloudformation",
            "SetStackPolicy": "cloudformation", "GetStackPolicy": "cloudformation",
            # EBS Snapshots
            # Note: CreateSnapshot, DeleteSnapshot, DescribeSnapshots are intentionally
            # omitted here because they conflict with ElastiCache actions of the same
            # name. These are routed via credential scope or host header instead.
            "CopySnapshot": "ec2", "ModifySnapshotAttribute": "ec2",
            "DescribeSnapshotAttribute": "ec2",
            # AutoScaling actions
            "CreateAutoScalingGroup": "autoscaling", "DescribeAutoScalingGroups": "autoscaling",
            "UpdateAutoScalingGroup": "autoscaling", "DeleteAutoScalingGroup": "autoscaling",
            "CreateLaunchConfiguration": "autoscaling", "DescribeLaunchConfigurations": "autoscaling",
            "DeleteLaunchConfiguration": "autoscaling",
            "PutScalingPolicy": "autoscaling", "DescribePolicies": "autoscaling",
            "DeletePolicy": "autoscaling",
            "PutLifecycleHook": "autoscaling", "DescribeLifecycleHooks": "autoscaling",
            "DeleteLifecycleHook": "autoscaling",
            "PutScheduledUpdateGroupAction": "autoscaling", "DescribeScheduledActions": "autoscaling",
            "DeleteScheduledAction": "autoscaling",
            "DescribeAutoScalingInstances": "autoscaling",
        }
        if action in action_service_map:
            return action_service_map[action]

    # 4. Check URL path patterns
    path_lower = path.lower()
    if path_lower.startswith("/v1/apis") or path_lower.startswith("/v1/tags/arn:aws:appsync"):
        return "appsync"
    if path_lower.startswith("/2020-05-31/"):
        return "cloudfront"
    if path_lower.startswith("/2013-04-01/"):
        return "route53"
    if path_lower.startswith("/v2/apis"):
        return "apigateway"
    if (path_lower.startswith("/restapis") or path_lower.startswith("/apikeys")
            or path_lower.startswith("/usageplans") or path_lower.startswith("/domainnames")):
        return "apigateway"
    if path_lower.startswith("/2015-03-31/functions"):
        return "lambda"
    if path_lower.startswith("/oauth2/token"):
        return "cognito-idp"
    if path_lower.startswith(("/clusters", "/taskdefinitions", "/tasks", "/services", "/stoptask")):
        return "ecs"
    # smithy-rpc-v2-cbor path: /service/ServiceName/operation/ActionName
    if "/service/" in path_lower and "/operation/" in path_lower:
        if "granite" in path_lower or "cloudwatch" in path_lower:
            return "monitoring"

    # 5. Check host header patterns
    for svc, patterns in SERVICE_PATTERNS.items():
        for hp in patterns.get("host_patterns", []):
            if re.search(hp, host):
                return svc

    # 6. Default to S3 (same as real LocalStack behavior)
    return "s3"


def extract_region(headers: dict) -> str:
    """Extract AWS region from the request."""
    auth = headers.get("authorization", "")
    match = re.search(r"Credential=[^/]+/[^/]+/([^/]+)/", auth)
    if match:
        return match.group(1)
    return os.environ.get("MINISTACK_REGION", "us-east-1")


def extract_access_key_id(headers: dict) -> str:
    """Extract the AWS access key ID from the Authorization header."""
    auth = headers.get("authorization", "")
    if auth:
        match = re.search(r"Credential=([^/]+)/", auth)
        if match:
            return match.group(1)
    return ""


def extract_account_id(headers: dict) -> str:
    """Extract account ID from credentials or env var.
    If the access key is a 12-digit number, use it as the account ID."""
    from ministack.core.responses import get_account_id
    return get_account_id()
