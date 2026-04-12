"""
GCP Services — Shared extended module.
Houses multiple lightweight GCP service handlers.
"""

import copy, json, time, uuid
from ministack.core.auth_gcp import GCP_PROJECT_ID, GCP_REGION
from ministack.core.responses import AccountScopedDict, new_uuid

# ── GCS (Cloud Storage) ───────────────────────────────────
_gcs_buckets = AccountScopedDict()

async def handle_storage_request(method, path, headers, body, query_params):
    # GET /storage/v1/b — list buckets
    if path.startswith("/storage/v1/b") and method == "GET" and "/o" not in path:
        buckets = [{"name": n, "projectNumber": GCP_PROJECT_ID} for n in _gcs_buckets.keys()]
        return 200, {"Content-Type": "application/json"}, json.dumps({"items": buckets}).encode()
    # POST /storage/v1/b — create bucket
    if path.startswith("/storage/v1/b") and method == "POST" and "/o" not in path:
        payload = json.loads(body) if body else {}
        name = payload.get("name", f"bucket-{new_uuid()[:8]}")
        bucket = {"name": name, "projectNumber": GCP_PROJECT_ID, "timeCreated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        _gcs_buckets[name] = bucket
        return 200, {"Content-Type": "application/json"}, json.dumps(bucket).encode()
    # DELETE /storage/v1/b/{bucket}
    if path.startswith("/storage/v1/b/") and method == "DELETE" and "/o" not in path:
        name = path.split("/storage/v1/b/")[-1].split("?")[0]
        if name in _gcs_buckets: del _gcs_buckets[name]
        return 204, {}, b""
    # Object operations: /storage/v1/b/{bucket}/o
    if "/o" in path:
        return _handle_object(method, path, headers, body)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _handle_object(method, path, headers, body):
    parts = path.split("/o")
    bucket_part = parts[0].split("/storage/v1/b/")[-1]
    rest = parts[1] if len(parts) > 1 else ""
    obj_name = rest.split("?")[0].strip("/") if rest else ""

    if method == "POST" and not obj_name:
        payload = json.loads(body) if body else {}
        name = payload.get("name", f"obj-{new_uuid()[:8]}")
        obj = {"name": name, "bucket": bucket_part, "size": len(body) if body else 0,
               "timeCreated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "md5Hash": "d41d8cd98f00b204e9800998ecf8427e"}
        _gcs_buckets.setdefault(bucket_part, {})["objects"] = _gcs_buckets.get(bucket_part, {}).get("objects", {})
        _gcs_buckets[bucket_part]["objects"][name] = obj
        return 200, {"Content-Type": "application/json"}, json.dumps(obj).encode()

    if method == "GET":
        if obj_name:
            bucket = _gcs_buckets.get(bucket_part, {})
            obj = bucket.get("objects", {}).get(obj_name)
            if obj: return 200, {"Content-Type": "application/json"}, json.dumps(obj).encode()
            return 404, {"Content-Type": "application/json"}, json.dumps({"error": "NotFound"}).encode()
        # List objects
        bucket = _gcs_buckets.get(bucket_part, {})
        objects = list(bucket.get("objects", {}).values())
        return 200, {"Content-Type": "application/json"}, json.dumps({"items": objects}).encode()

    if method == "DELETE" and obj_name:
        bucket = _gcs_buckets.get(bucket_part, {})
        if obj_name in bucket.get("objects", {}): del bucket["objects"][obj_name]
        return 204, {}, b""
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def reset_storage(): _gcs_buckets.clear()

# ── Pub/Sub ───────────────────────────────────────────────
_pubsub_topics = AccountScopedDict()
_pubsub_subscriptions = AccountScopedDict()
_pubsub_messages = []

async def handle_pubsub_request(method, path, headers, body, query_params):
    # /v1/projects/{proj}/topics
    if "/topics" in path and method == "PUT":
        payload = json.loads(body) if body else {}
        name = path.split("/topics/")[-1] if "/topics/" in path else payload.get("name", f"topic-{new_uuid()[:8]}")
        topic = {"name": f"projects/{GCP_PROJECT_ID}/topics/{name}", "labels": {}}
        _pubsub_topics[name] = topic
        return 200, {"Content-Type": "application/json"}, json.dumps(topic).encode()
    if "/topics" in path and method == "GET":
        return 200, {"Content-Type": "application/json"}, json.dumps({"topics": list(_pubsub_topics.values())}).encode()
    if "/topics" in path and method == "DELETE":
        name = path.split("/topics/")[-1].split("?")[0]
        if name in _pubsub_topics: del _pubsub_topics[name]
        return 200, {"Content-Type": "application/json"}, b"{}"
    # Publish: /v1/projects/{proj}/topics/{name}:publish
    if ":publish" in path and method == "POST":
        payload = json.loads(body) if body else {}
        msgs = []
        for m in payload.get("messages", []):
            msg = {"messageId": new_uuid(), "publishTime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "data": m.get("data", "")}
            _pubsub_messages.append(msg)
            msgs.append({"messageId": msg["messageId"]})
        return 200, {"Content-Type": "application/json"}, json.dumps({"messageIds": [m["messageId"] for m in msgs]}).encode()
    # Subscriptions
    if "/subscriptions" in path and method == "PUT":
        payload = json.loads(body) if body else {}
        name = path.split("/subscriptions/")[-1] if "/subscriptions/" in path else payload.get("name", f"sub-{new_uuid()[:8]}")
        sub = {"name": f"projects/{GCP_PROJECT_ID}/subscriptions/{name}", "topic": payload.get("topic", ""), "ackDeadlineSeconds": 10}
        _pubsub_subscriptions[name] = sub
        return 200, {"Content-Type": "application/json"}, json.dumps(sub).encode()
    if "/subscriptions" in path and method == "GET":
        return 200, {"Content-Type": "application/json"}, json.dumps({"subscriptions": list(_pubsub_subscriptions.values())}).encode()
    # Pull
    if ":pull" in path and method == "POST":
        if _pubsub_messages:
            msg = _pubsub_messages.pop(0)
            return 200, {"Content-Type": "application/json"}, json.dumps({"receivedMessages": [{"ackId": new_uuid(), "message": msg}]}).encode()
        return 200, {"Content-Type": "application/json"}, json.dumps({"receivedMessages": []}).encode()
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def reset_pubsub(): _pubsub_topics.clear(); _pubsub_subscriptions.clear(); _pubsub_messages.clear()

# ── Cloud Functions ───────────────────────────────────────
_gcf_functions = AccountScopedDict()

async def handle_functions_request(method, path, headers, body, query_params):
    if method in ("POST", "PUT") and ("/functions" in path or "/v2/" in path):
        name = path.split("/functions/")[-1].split("?")[0] if "/functions/" in path else f"fn-{new_uuid()[:8]}"
        payload = json.loads(body) if body else {}
        fn = {"name": f"projects/{GCP_PROJECT_ID}/locations/{GCP_REGION}/functions/{name}",
              "status": "ACTIVE", "entryPoint": payload.get("entryPoint", "handler"),
              "runtime": payload.get("runtime", "python311"), "httpsTrigger": {"url": f"http://localhost:4566/gcp/fn/{name}"}}
        _gcf_functions[name] = fn
        return 200, {"Content-Type": "application/json"}, json.dumps({"name": fn["name"], "metadata": fn, "done": True}).encode()
    if method == "GET" and "/functions" in path:
        return 200, {"Content-Type": "application/json"}, json.dumps({"functions": list(_gcf_functions.values())}).encode()
    if method == "DELETE" and "/functions/" in path:
        name = path.split("/functions/")[-1].split("?")[0]
        if name in _gcf_functions: del _gcf_functions[name]
        return 200, {"Content-Type": "application/json"}, json.dumps({"name": name, "done": True}).encode()
    # Invoke
    if path.startswith("/gcp/fn/") and method == "POST":
        name = path.split("/gcp/fn/")[-1].split("?")[0]
        if name not in _gcf_functions:
            return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Function not found"}).encode()
        payload = json.loads(body) if body else {}
        return 200, {"Content-Type": "application/json"}, json.dumps({"result": "OK", "input": payload}).encode()
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def reset_functions(): _gcf_functions.clear()

# ── BigQuery ──────────────────────────────────────────────
_bq_datasets = AccountScopedDict()
_bq_jobs = []

async def handle_bigquery_request(method, path, headers, body, query_params):
    if "/datasets" in path and method in ("POST", "PUT"):
        payload = json.loads(body) if body else {}
        ds_id = payload.get("datasetReference", {}).get("datasetId", f"ds_{new_uuid()[:8]}")
        ds = {"datasetReference": {"projectId": GCP_PROJECT_ID, "datasetId": ds_id}, "id": ds_id}
        _bq_datasets[ds_id] = ds
        return 200, {"Content-Type": "application/json"}, json.dumps(ds).encode()
    if "/datasets" in path and method == "GET":
        return 200, {"Content-Type": "application/json"}, json.dumps({"datasets": [{"datasetReference": d["datasetReference"], "id": d["id"]} for d in _bq_datasets.values()]}).encode()
    if "/jobs" in path and method == "POST":
        payload = json.loads(body) if body else {}
        job_id = f"job-{new_uuid()[:12]}"
        job = {"jobReference": {"jobId": job_id, "projectId": GCP_PROJECT_ID}, "status": {"state": "DONE"}, "configuration": payload.get("configuration", {})}
        _bq_jobs.append(job)
        return 200, {"Content-Type": "application/json"}, json.dumps(job).encode()
    if "/jobs" in path and method == "GET":
        return 200, {"Content-Type": "application/json"}, json.dumps({"jobs": _bq_jobs}).encode()
    if "/query" in path and method == "POST":
        payload = json.loads(body) if body else {}
        return 200, {"Content-Type": "application/json"}, json.dumps({"jobReference": {"jobId": new_uuid()}, "rows": [], "totalRows": "0", "query": payload.get("query", "")}).encode()
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def reset_bigquery(): _bq_datasets.clear(); _bq_jobs.clear()

# ── Cloud SQL ─────────────────────────────────────────────
_sql_instances = AccountScopedDict()

async def handle_sql_request(method, path, headers, body, query_params):
    if "/instances" in path and method in ("POST", "PUT"):
        payload = json.loads(body) if body else {}
        name = payload.get("name", f"sql-{new_uuid()[:8]}")
        inst = {"name": name, "state": "RUNNABLE", "databaseVersion": payload.get("databaseVersion", "POSTGRES_14"),
                "ipAddresses": [{"ipAddress": "127.0.0.1", "type": "PRIMARY"}], "region": GCP_REGION}
        _sql_instances[name] = inst
        return 200, {"Content-Type": "application/json"}, json.dumps({"kind": "sql#instance", "name": name, "state": "RUNNABLE", "databaseVersion": inst["databaseVersion"], "ipAddresses": inst["ipAddresses"]}).encode()
    if "/instances" in path and method == "GET":
        return 200, {"Content-Type": "application/json"}, json.dumps({"kind": "sql#instancesList", "items": list(_sql_instances.values())}).encode()
    if "/instances/" in path and method == "DELETE":
        name = path.split("/instances/")[-1].split("?")[0]
        if name in _sql_instances: del _sql_instances[name]
        return 200, {"Content-Type": "application/json"}, b"{}"
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def reset_sql(): _sql_instances.clear()

# ── Cloud Run ─────────────────────────────────────────────
_run_services = AccountScopedDict()

async def handle_run_request(method, path, headers, body, query_params):
    if method in ("POST", "PUT"):
        name = f"svc-{new_uuid()[:8]}"
        svc = {"apiVersion": "serving.knative.dev/v1", "kind": "Service",
               "metadata": {"name": name, "namespace": GCP_PROJECT_ID},
               "status": {"url": f"https://{name}-{new_uuid()[:6]}-uc.a.run.app", "conditions": [{"type": "Ready", "status": "True"}]}}
        _run_services[name] = svc
        return 200, {"Content-Type": "application/json"}, json.dumps(svc).encode()
    if method == "GET":
        return 200, {"Content-Type": "application/json"}, json.dumps({"kind": "ServiceList", "items": list(_run_services.values())}).encode()
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def reset_run(): _run_services.clear()

# ── Cloud Logging ─────────────────────────────────────────
_logging_entries = []

async def handle_logging_request(method, path, headers, body, query_params):
    if "/entries:write" in path and method == "POST":
        payload = json.loads(body) if body else {}
        entries = payload.get("entries", [])
        for e in entries:
            _logging_entries.append({"logName": e.get("logName", ""), "resource": e.get("resource", {}), "textPayload": e.get("textPayload", ""), "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        return 200, {"Content-Type": "application/json"}, b"{}"
    if "/entries" in path and method == "GET":
        return 200, {"Content-Type": "application/json"}, json.dumps({"entries": _logging_entries}).encode()
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def reset_logging(): _logging_entries.clear()

# ── Cloud Monitoring ──────────────────────────────────────
_monitoring_metrics = []

async def handle_monitoring_request(method, path, headers, body, query_params):
    if "/timeSeries" in path and method == "POST":
        payload = json.loads(body) if body else {}
        _monitoring_metrics.append({"series": payload.get("timeSeries", []), "timestamp": time.time()})
        return 200, {"Content-Type": "application/json"}, b"{}"
    if "/timeSeries" in path and method == "GET":
        return 200, {"Content-Type": "application/json"}, json.dumps({"timeSeries": []}).encode()
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def reset_monitoring(): _monitoring_metrics.clear()

# ── Secret Manager ────────────────────────────────────────
_secrets = AccountScopedDict()

async def handle_secretmanager_request(method, path, headers, body, query_params):
    if "/secrets" in path and method == "POST":
        payload = json.loads(body) if body else {}
        name = path.split("/secrets:")[-1].split("?")[0] if ":addVersion" not in path else path.split("/secrets/")[-1].split("/")[0]
        if ":addVersion" not in path:
            secret = {"name": f"projects/{GCP_PROJECT_ID}/secrets/{name}", "replication": {"automatic": {}}, "labels": {}}
            _secrets[name] = {"secret": secret, "versions": []}
            return 200, {"Content-Type": "application/json"}, json.dumps(secret).encode()
    if ":addVersion" in path and method == "POST":
        name = path.split("/secrets/")[-1].split(":addVersion")[0]
        payload = json.loads(body) if body else {}
        version = {"name": f"projects/{GCP_PROJECT_ID}/secrets/{name}/versions/1", "state": "ENABLED"}
        if name in _secrets: _secrets[name]["versions"].append(version)
        return 200, {"Content-Type": "application/json"}, json.dumps(version).encode()
    if "/secrets" in path and method == "GET":
        if "/versions/" in path:
            return 200, {"Content-Type": "application/json"}, json.dumps({"versions": []}).encode()
        return 200, {"Content-Type": "application/json"}, json.dumps({"secrets": [v["secret"] for v in _secrets.values()]}).encode()
    if ":access" in path and method == "GET":
        return 200, {"Content-Type": "application/json"}, json.dumps({"payload": {"data": "dGVzdC1zZWNyZXQ=", "dataCrc32C": "0"}}).encode()
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def reset_secretmanager(): _secrets.clear()

# ── Cloud KMS ─────────────────────────────────────────────
_kms_keyrings = AccountScopedDict()

async def handle_kms_request(method, path, headers, body, query_params):
    if "/keyRings" in path and method == "POST":
        payload = json.loads(body) if body else {}
        name = path.split("/keyRings/")[-1].split("?")[0] if "/keyRings/" in path else f"kr-{new_uuid()[:8]}"
        kr = {"name": f"projects/{GCP_PROJECT_ID}/locations/{GCP_REGION}/keyRings/{name}"}
        _kms_keyrings[name] = {"keyRing": kr, "keys": []}
        return 200, {"Content-Type": "application/json"}, json.dumps(kr).encode()
    if "/cryptoKeys" in path and method == "POST":
        payload = json.loads(body) if body else {}
        name = payload.get("name", f"key-{new_uuid()[:8]}")
        key = {"name": f"projects/{GCP_PROJECT_ID}/locations/{GCP_REGION}/keyRings/.../cryptoKeys/{name}",
               "primary": {"name": ".../cryptoKeyVersions/1", "state": "ENABLED"}, "purpose": "ENCRYPT_DECRYPT"}
        for kr in _kms_keyrings.values(): kr["keys"].append(key)
        return 200, {"Content-Type": "application/json"}, json.dumps(key).encode()
    if "/keyRings" in path and method == "GET":
        return 200, {"Content-Type": "application/json"}, json.dumps({"keyRings": [v["keyRing"] for v in _kms_keyrings.values()]}).encode()
    if "/cryptoKeys" in path and method == "GET":
        keys = []
        for kr in _kms_keyrings.values(): keys.extend(kr["keys"])
        return 200, {"Content-Type": "application/json"}, json.dumps({"cryptoKeys": keys}).encode()
    if ":encrypt" in path and method == "POST":
        return 200, {"Content-Type": "application/json"}, json.dumps({"ciphertext": "base64stub"}).encode()
    if ":decrypt" in path and method == "POST":
        return 200, {"Content-Type": "application/json"}, json.dumps({"plaintext": "base64stub"}).encode()
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def reset_kms(): _kms_keyrings.clear()

# ── Compute Engine ────────────────────────────────────────
_compute_instances = AccountScopedDict()

async def handle_compute_request(method, path, headers, body, query_params):
    if "/instances" in path and method == "POST":
        payload = json.loads(body) if body else {}
        name = payload.get("name", f"vm-{new_uuid()[:8]}")
        vm = {"kind": "compute#instance", "name": name, "status": "RUNNING", "machineType": payload.get("machineType", "n1-standard-1"),
              "disks": [{"boot": True, "type": "PERSISTENT"}], "networkInterfaces": [{"networkIP": "10.0.0.2", "accessConfigs": [{"natIP": "34.0.0.1"}]}],
              "zone": f"projects/{GCP_PROJECT_ID}/zones/{GCP_ZONE}"}
        _compute_instances[name] = vm
        return 200, {"Content-Type": "application/json"}, json.dumps({"kind": "compute#operation", "name": new_uuid(), "status": "DONE", "targetLink": vm["selfLink"] if "selfLink" in vm else ""}).encode()
    if "/instances" in path and method == "GET":
        return 200, {"Content-Type": "application/json"}, json.dumps({"kind": "compute#instanceList", "items": list(_compute_instances.values())}).encode()
    if "/instances/" in path and method == "DELETE":
        name = path.split("/instances/")[-1].split("?")[0]
        if name in _compute_instances: del _compute_instances[name]
        return 200, {"Content-Type": "application/json"}, json.dumps({"kind": "compute#operation", "status": "DONE"}).encode()
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def reset_compute(): _compute_instances.clear()

# ── Artifact Registry ─────────────────────────────────────
_ar_repos = AccountScopedDict()

async def handle_artifactregistry_request(method, path, headers, body, query_params):
    if "/repositories" in path and method == "POST":
        payload = json.loads(body) if body else {}
        name = payload.get("name", f"repo-{new_uuid()[:8]}").split("/")[-1]
        repo = {"name": f"projects/{GCP_PROJECT_ID}/locations/{GCP_REGION}/repositories/{name}", "format": "DOCKER"}
        _ar_repos[name] = repo
        return 200, {"Content-Type": "application/json"}, json.dumps(repo).encode()
    if "/repositories" in path and method == "GET":
        return 200, {"Content-Type": "application/json"}, json.dumps({"repositories": list(_ar_repos.values())}).encode()
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def reset_artifactregistry(): _ar_repos.clear()

# ── Metadata Server ───────────────────────────────────────
from ministack.core.auth_gcp import get_metadata_endpoint as _meta_endpoint

async def handle_metadata_request(method, path, headers, body, query_params):
    status, hdrs, resp = _meta_endpoint(path)
    return status, hdrs, resp

def reset_metadata(): pass

# ── IAM ───────────────────────────────────────────────────
_gcp_iam_service_accounts = AccountScopedDict()

async def handle_iam_request(method, path, headers, body, query_params):
    if "/serviceAccounts" in path and method == "POST":
        payload = json.loads(body) if body else {}
        email = payload.get("accountId", f"sa-{new_uuid()[:8]}") + f"@{GCP_PROJECT_ID}.iam.gserviceaccount.com"
        sa = {"name": f"projects/{GCP_PROJECT_ID}/serviceAccounts/{email}", "email": email, "projectId": GCP_PROJECT_ID, "uniqueId": new_uuid()}
        _gcp_iam_service_accounts[email] = sa
        return 200, {"Content-Type": "application/json"}, json.dumps(sa).encode()
    if "/serviceAccounts" in path and method == "GET":
        return 200, {"Content-Type": "application/json"}, json.dumps({"accounts": list(_gcp_iam_service_accounts.values())}).encode()
    if "/serviceAccounts/" in path and method == "DELETE":
        email = path.split("/serviceAccounts/")[-1].split("?")[0]
        if email in _gcp_iam_service_accounts: del _gcp_iam_service_accounts[email]
        return 200, {"Content-Type": "application/json"}, b"{}"
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def reset_iam(): _gcp_iam_service_accounts.clear()

# ── Reset all GCP services ────────────────────────────────
def reset_all():
    reset_storage()
    reset_pubsub()
    reset_functions()
    reset_bigquery()
    reset_sql()
    reset_run()
    reset_logging()
    reset_monitoring()
    reset_secretmanager()
    reset_kms()
    reset_compute()
    reset_artifactregistry()
    reset_iam()
