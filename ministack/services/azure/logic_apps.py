"""Azure Logic Apps."""
import copy, json, time, uuid
from ministack.core.responses import AccountScopedDict, new_uuid
_workflows = AccountScopedDict()

async def handle_request(method, path, headers, body, query_params):
    if "/workflows/" in path and method in ("PUT", "POST"): return _create_workflow(path, body)
    if "/workflows" in path and method == "GET": return _list_workflows(path)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _create_workflow(path, body):
    payload = json.loads(body) if body else {}
    name = payload.get("name", f"workflow-{new_uuid()[:8]}")
    w = {"name": name, "state": "Enabled", "definition": payload.get("properties", {}).get("definition", {})}
    _workflows[name] = w
    return 200, {"Content-Type": "application/json"}, json.dumps({"name": name, "properties": w}).encode()

def _list_workflows(path): return 200, {"Content-Type": "application/json"}, json.dumps({"value": [{"name": n, "properties": w} for n, w in _workflows.items()]}).encode()
def reset(): _workflows.clear()
def get_state(): return {"workflows": copy.deepcopy(_workflows)}
