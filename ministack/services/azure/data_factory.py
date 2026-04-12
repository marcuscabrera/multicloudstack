"""Azure Data Factory."""
import copy, json, time, uuid
from ministack.core.responses import AccountScopedDict, new_uuid
_factories = AccountScopedDict()

async def handle_request(method, path, headers, body, query_params):
    if "/factories/" in path and method in ("PUT", "POST"): return _create_factory(path, body)
    if "/factories" in path and method == "GET": return _list_factories(path)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _create_factory(path, body):
    payload = json.loads(body) if body else {}
    name = payload.get("name", f"adf-{new_uuid()[:8]}")
    f = {"name": name, "location": "eastus", "provisioningState": "Succeeded"}
    _factories[name] = f
    return 200, {"Content-Type": "application/json"}, json.dumps({"name": name, "properties": f}).encode()

def _list_factories(path): return 200, {"Content-Type": "application/json"}, json.dumps({"value": [{"name": n, "properties": f} for n, f in _factories.items()]}).encode()
def reset(): _factories.clear()
def get_state(): return {"factories": copy.deepcopy(_factories)}
