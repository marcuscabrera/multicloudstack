"""Azure Container Registry (ACR)."""
import copy, json, time, uuid
from ministack.core.responses import AccountScopedDict, new_uuid
_registries = AccountScopedDict()

async def handle_request(method, path, headers, body, query_params):
    if "/registries/" in path and method in ("PUT", "POST"): return _create_registry(path, body)
    if "/registries" in path and method == "GET": return _list_registries(path)
    if "/registries/" in path and method == "DELETE": return _delete_registry(path)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _create_registry(path, body):
    payload = json.loads(body) if body else {}
    name = payload.get("name", f"acr-{new_uuid()[:8]}")
    reg = {"name": name, "loginServer": f"{name}.azurecr.local", "provisioningState": "Succeeded", "adminUserEnabled": True}
    _registries[name] = reg
    return 200, {"Content-Type": "application/json"}, json.dumps({"name": name, "properties": reg}).encode()

def _list_registries(path): return 200, {"Content-Type": "application/json"}, json.dumps({"value": [{"name": n, "properties": r} for n, r in _registries.items()]}).encode()
def _delete_registry(path):
    name = path.split("/registries/")[-1].split("?")[0].split("/")[0]
    if name in _registries: del _registries[name]
    return 202, {"Content-Type": "application/json"}, b"{}"

def reset(): _registries.clear()
def get_state(): return {"registries": copy.deepcopy(_registries)}
