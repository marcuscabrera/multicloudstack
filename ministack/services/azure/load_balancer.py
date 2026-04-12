"""Azure Load Balancer / App Gateway."""
import copy, json, time, uuid
from ministack.core.responses import AccountScopedDict, new_uuid
_lbs = AccountScopedDict()

async def handle_request(method, path, headers, body, query_params):
    if "/loadBalancers/" in path and method in ("PUT", "POST"): return _create_lb(path, body)
    if "/loadBalancers" in path and method == "GET": return _list_lbs(path)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _create_lb(path, body):
    payload = json.loads(body) if body else {}
    name = payload.get("name", f"lb-{new_uuid()[:8]}")
    lb = {"name": name, "frontendIPConfigurations": [], "provisioningState": "Succeeded"}
    _lbs[name] = lb
    return 200, {"Content-Type": "application/json"}, json.dumps({"name": name, "properties": lb}).encode()

def _list_lbs(path): return 200, {"Content-Type": "application/json"}, json.dumps({"value": [{"name": n, "properties": lb} for n, lb in _lbs.items()]}).encode()
def reset(): _lbs.clear()
def get_state(): return {"lbs": copy.deepcopy(_lbs)}
