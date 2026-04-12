"""Azure CDN / Front Door."""
import copy, json, time, uuid
from ministack.core.responses import AccountScopedDict, new_uuid
_profiles = AccountScopedDict()

async def handle_request(method, path, headers, body, query_params):
    if "/profiles/" in path and method in ("PUT", "POST"): return _create_profile(path, body)
    if "/profiles" in path and method == "GET": return _list_profiles(path)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _create_profile(path, body):
    payload = json.loads(body) if body else {}
    name = payload.get("name", f"cdn-{new_uuid()[:8]}")
    p = {"name": name, "endpoint": f"{name}.azureedge.local", "provisioningState": "Succeeded"}
    _profiles[name] = p
    return 200, {"Content-Type": "application/json"}, json.dumps({"name": name, "properties": p}).encode()

def _list_profiles(path): return 200, {"Content-Type": "application/json"}, json.dumps({"value": [{"name": n, "properties": p} for n, p in _profiles.items()]}).encode()
def reset(): _profiles.clear()
def get_state(): return {"profiles": copy.deepcopy(_profiles)}
