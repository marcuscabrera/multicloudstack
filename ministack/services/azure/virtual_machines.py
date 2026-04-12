"""Azure Virtual Machines (control plane)."""
import copy, json, time, uuid
from ministack.core.responses import AccountScopedDict, new_uuid
_vms = AccountScopedDict()

async def handle_request(method, path, headers, body, query_params):
    if "/virtualMachines/" in path and method in ("PUT", "POST"): return _create_vm(path, body)
    if "/virtualMachines" in path and method == "GET": return _list_vms(path)
    if "/virtualMachines/" in path and method == "GET": return _get_vm(path)
    if "/virtualMachines/" in path and method == "DELETE": return _delete_vm(path)
    if "/virtualMachines/" in path and method == "POST": return _vm_action(path, body)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _create_vm(path, body):
    payload = json.loads(body) if body else {}
    name = payload.get("name", f"vm-{new_uuid()[:8]}")
    vm = {"name": name, "vmSize": payload.get("vmSize", "Standard_DS2_v2"), "provisioningState": "Succeeded",
          "osProfile": payload.get("osProfile", {}), "status": "running"}
    _vms[name] = vm
    return 200, {"Content-Type": "application/json"}, json.dumps({"name": name, "properties": vm}).encode()

def _list_vms(path): return 200, {"Content-Type": "application/json"}, json.dumps({"value": [{"name": n, "properties": v} for n, v in _vms.items()]}).encode()
def _get_vm(path):
    name = path.split("/virtualMachines/")[-1].split("?")[0].split("/")[0]
    v = _vms.get(name)
    return (200, {"Content-Type": "application/json"}, json.dumps({"name": name, "properties": v})) if v else (404, {"Content-Type": "application/json"}, json.dumps({"error": "VMNotFound"}).encode())
def _delete_vm(path):
    name = path.split("/virtualMachines/")[-1].split("?")[0].split("/")[0]
    if name in _vms: del _vms[name]
    return 202, {"Content-Type": "application/json"}, b"{}"
def _vm_action(path, body):
    payload = json.loads(body) if body else {}
    name = path.split("/virtualMachines/")[-1].split("?")[0].split("/")[0]
    if name in _vms: _vms[name]["status"] = payload.get("properties", {}).get("additionalProperties", "running")
    return 202, {"Content-Type": "application/json"}, b"{}"

def reset(): _vms.clear()
def get_state(): return {"vms": copy.deepcopy(_vms)}
