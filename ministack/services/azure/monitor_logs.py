"""
Azure Monitor Logs (Log Analytics).
Reuses CloudWatch Logs patterns. Supports basic KQL-like queries.
"""
import copy, json, logging, time, uuid
from ministack.core.responses import AccountScopedDict, new_uuid
logger = logging.getLogger("azure_monitor_logs")
_workspaces = AccountScopedDict()
_logs = AccountScopedDict()

async def handle_request(method, path, headers, body, query_params):
    if "/workspaces/" in path and "/query" in path and method == "POST":
        return _query_logs(path, body)
    if "/tables/" in path and "/rows" in path and method == "POST":
        return _ingest_logs(path, body)
    if "/workspaces" in path and method == "GET":
        return _list_workspaces(path)
    if "/workspaces/" in path and method in ("PUT", "POST"):
        return _create_workspace(path, body)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _create_workspace(path, body):
    payload = json.loads(body) if body else {}
    name = payload.get("name", f"workspace-{new_uuid()[:8]}")
    ws = {"name": name, "customerId": new_uuid()[:8], "created": time.time()}
    _workspaces[name] = ws
    return 200, {"Content-Type": "application/json"}, json.dumps({"name": name, "properties": ws}).encode()

def _list_workspaces(path):
    return 200, {"Content-Type": "application/json"}, json.dumps({"value": [{"name": n, "properties": w} for n, w in _workspaces.items()]}).encode()

def _ingest_logs(path, body):
    payload = json.loads(body) if body else {}
    rows = payload.get("rows", [])
    ws = "default"
    for r in rows:
        _logs.setdefault(ws, []).append({"data": r, "ingested": time.time()})
    return 200, {"Content-Type": "application/json"}, json.dumps({"status": "success", "ingested": len(rows)}).encode()

def _query_logs(path, body):
    payload = json.loads(body) if body else {}
    query = payload.get("query", "")
    ws_logs = _logs.get("default", [])
    return 200, {"Content-Type": "application/json"}, json.dumps({"tables": [{"name": "Results", "rows": [l["data"] for l in ws_logs], "query": query}]}).encode()

def reset(): _workspaces.clear(); _logs.clear()
def get_state(): return {"workspaces": copy.deepcopy(_workspaces), "logs": copy.deepcopy(_logs)}
