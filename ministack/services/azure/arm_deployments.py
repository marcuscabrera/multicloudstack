"""Azure Resource Manager — ARM Deployments (JSON templates)."""
import copy, json, logging, time, uuid
from ministack.core.responses import AccountScopedDict, new_uuid
from ministack.core.azure_resource_id import extract_subscription_id, extract_resource_group
logger = logging.getLogger("azure_arm")
_deployments = AccountScopedDict()

async def handle_request(method, path, headers, body, query_params):
    if "/deployments/" in path and method in ("PUT", "POST"): return _create_deployment(path, body)
    if "/deployments/" in path and method == "GET": return _get_deployment(path)
    if "/deployments" in path and method == "GET": return _list_deployments(path)
    if "/deployments/" in path and method == "DELETE": return _delete_deployment(path)
    if "/operations" in path and method == "GET": return _list_operations(path)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _create_deployment(path, body):
    payload = json.loads(body) if body else {}
    name = payload.get("name", f"deploy-{new_uuid()[:8]}")
    props = payload.get("properties", {})
    tmpl = props.get("template", {})
    resources = tmpl.get("resources", [])
    dep = {"name": name, "properties": {"provisioningState": "Succeeded", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "parameters": props.get("parameters", {}), "outputs": tmpl.get("outputs", {}), "resources": len(resources)}}
    _deployments[name] = dep
    return 200, {"Content-Type": "application/json"}, json.dumps(dep).encode()

def _get_deployment(path):
    name = path.split("/deployments/")[-1].split("?")[0].split("/")[0]
    d = _deployments.get(name)
    return (200, {"Content-Type": "application/json"}, json.dumps(d)) if d else (404, {"Content-Type": "application/json"}, json.dumps({"error": "DeploymentNotFound"}).encode())

def _list_deployments(path):
    return 200, {"Content-Type": "application/json"}, json.dumps({"value": [{"name": n, "properties": d["properties"]} for n, d in _deployments.items()]}).encode()

def _delete_deployment(path):
    name = path.split("/deployments/")[-1].split("?")[0].split("/")[0]
    if name in _deployments: del _deployments[name]
    return 202, {"Content-Type": "application/json"}, b"{}"

def _list_operations(path):
    return 200, {"Content-Type": "application/json"}, json.dumps({"value": [{"operationId": new_uuid(), "status": "Succeeded"} for _ in _deployments]}).encode()

def reset(): _deployments.clear()
def get_state(): return {"deployments": copy.deepcopy(_deployments)}
