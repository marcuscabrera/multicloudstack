"""Azure Container Instances (ACI)."""
import copy, json, time, uuid
from ministack.core.responses import AccountScopedDict, new_uuid
_groups = AccountScopedDict()

async def handle_request(method, path, headers, body, query_params):
    if "/containerGroups/" in path and method in ("PUT", "POST"): return _create_group(path, body)
    if "/containerGroups" in path and method == "GET": return _list_groups(path)
    if "/containerGroups/" in path and method == "GET": return _get_group(path)
    if "/containerGroups/" in path and method == "DELETE": return _delete_group(path)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _create_group(path, body):
    payload = json.loads(body) if body else {}
    name = payload.get("name", f"aci-{new_uuid()[:8]}")
    grp = {"name": name, "containers": payload.get("properties", {}).get("containers", []), "ipAddress": "10.0.0.1", "provisioningState": "Succeeded"}
    _groups[name] = grp
    return 200, {"Content-Type": "application/json"}, json.dumps({"name": name, "properties": grp}).encode()

def _list_groups(path): return 200, {"Content-Type": "application/json"}, json.dumps({"value": [{"name": n, "properties": g} for n, g in _groups.items()]}).encode()
def _get_group(path):
    name = path.split("/containerGroups/")[-1].split("?")[0].split("/")[0]
    g = _groups.get(name)
    return (200, {"Content-Type": "application/json"}, json.dumps({"name": name, "properties": g})) if g else (404, {"Content-Type": "application/json"}, json.dumps({"error": "NotFound"}).encode())
def _delete_group(path):
    name = path.split("/containerGroups/")[-1].split("?")[0].split("/")[0]
    if name in _groups: del _groups[name]
    return 202, {"Content-Type": "application/json"}, b"{}"

def reset(): _groups.clear()
def get_state(): return {"groups": copy.deepcopy(_groups)}
