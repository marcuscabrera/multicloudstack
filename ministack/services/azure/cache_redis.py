"""
Azure Cache for Redis.
Reuses ElastiCache patterns.
"""
import copy, json, logging, os, time, uuid
from ministack.core.responses import AccountScopedDict, new_uuid
logger = logging.getLogger("azure_cache_redis")
_instances = AccountScopedDict()
BASE_PORT = int(os.environ.get("AZURE_REDIS_BASE_PORT", "16379"))
_port_counter = [BASE_PORT]

async def handle_request(method, path, headers, body, query_params):
    if "/redis/" in path and method in ("PUT", "POST"):
        return _create_instance(path, body)
    if "/redis" in path and method == "GET":
        return _list_instances(path)
    if "/redis/" in path and method == "GET":
        return _get_instance(path)
    if "/redis/" in path and method == "DELETE":
        return _delete_instance(path)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _name(path):
    for p in path.split("/"):
        if p and p not in ("redis", "Microsoft.Cache", "resourceGroups", "providers", "subscriptions") and not p.startswith("0000"):
            return p
    return ""

def _create_instance(path, body):
    payload = json.loads(body) if body else {}
    name = _name(path) or f"redis-{new_uuid()[:8]}"
    port = _port_counter[0]; _port_counter[0] += 1
    props = payload.get("properties", {})
    inst = {"hostName": "localhost", "port": port, "sslPort": port + 10000, "provisioningState": "Succeeded",
            "redisVersion": props.get("redisVersion", "6"), "sku": props.get("sku", {"name": "Basic", "capacity": 1})}
    _instances[name] = inst
    return 200, {"Content-Type": "application/json"}, json.dumps({"name": name, "properties": inst}).encode()

def _list_instances(path):
    return 200, {"Content-Type": "application/json"}, json.dumps({"value": [{"name": n, "properties": i} for n, i in _instances.items()]}).encode()

def _get_instance(path):
    name = _name(path)
    i = _instances.get(name)
    return (200, {"Content-Type": "application/json"}, json.dumps({"name": name, "properties": i})) if i else (404, {"Content-Type": "application/json"}, json.dumps({"error": "NotFound"}).encode())

def _delete_instance(path):
    name = _name(path)
    if name in _instances: del _instances[name]
    return 202, {"Content-Type": "application/json"}, b"{}"

def reset(): _instances.clear(); _port_counter[0] = BASE_PORT
def get_state(): return {"instances": copy.deepcopy(_instances)}
