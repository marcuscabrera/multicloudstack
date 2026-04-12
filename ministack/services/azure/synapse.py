"""Azure Synapse Analytics."""
import copy, json, time, uuid
from ministack.core.responses import AccountScopedDict, new_uuid
_workspaces = AccountScopedDict()

async def handle_request(method, path, headers, body, query_params):
    if "/workspaces/" in path and "/sql" in path and method == "POST": return _execute_sql(path, body)
    if "/workspaces/" in path and method in ("PUT", "POST"): return _create_workspace(path, body)
    if "/workspaces" in path and method == "GET": return _list_workspaces(path)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _create_workspace(path, body):
    payload = json.loads(body) if body else {}
    name = payload.get("name", f"synapse-{new_uuid()[:8]}")
    w = {"name": name, "sqlEndpoint": f"{name}.sql.local", "provisioningState": "Succeeded"}
    _workspaces[name] = w
    return 200, {"Content-Type": "application/json"}, json.dumps({"name": name, "properties": w}).encode()

def _list_workspaces(path): return 200, {"Content-Type": "application/json"}, json.dumps({"value": [{"name": n, "properties": w} for n, w in _workspaces.items()]}).encode()
def _execute_sql(path, body):
    payload = json.loads(body) if body else {}
    return 200, {"Content-Type": "application/json"}, json.dumps({"rows": [], "query": payload.get("query", "")}).encode()
def reset(): _workspaces.clear()
def get_state(): return {"workspaces": copy.deepcopy(_workspaces)}
