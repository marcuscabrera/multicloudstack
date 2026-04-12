"""Azure API Management."""
import copy, json, time, uuid
from ministack.core.responses import AccountScopedDict, new_uuid
_services = AccountScopedDict()

async def handle_request(method, path, headers, body, query_params):
    if "/service/" in path and method in ("PUT", "POST"): return _create_service(path, body)
    if "/service" in path and method == "GET": return _list_services(path)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _create_service(path, body):
    payload = json.loads(body) if body else {}
    name = payload.get("name", f"apim-{new_uuid()[:8]}")
    s = {"name": name, "gatewayUrl": f"http://localhost:4566/apim/{name}", "provisioningState": "Succeeded"}
    _services[name] = s
    return 200, {"Content-Type": "application/json"}, json.dumps({"name": name, "properties": s}).encode()

def _list_services(path): return 200, {"Content-Type": "application/json"}, json.dumps({"value": [{"name": n, "properties": s} for n, s in _services.items()]}).encode()
def reset(): _services.clear()
def get_state(): return {"services": copy.deepcopy(_services)}
