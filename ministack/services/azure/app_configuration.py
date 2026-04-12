"""Azure App Configuration."""
import copy, json, time, uuid
from ministack.core.responses import AccountScopedDict, new_uuid
_kvs = AccountScopedDict()

async def handle_request(method, path, headers, body, query_params):
    if "/kv/" in path and method in ("PUT", "POST"): return _set_kv(path, body)
    if "/kv/" in path and method == "GET": return _get_kv(path)
    if "/kv" in path and method == "GET": return _list_kv(path)
    if "/kv/" in path and method == "DELETE": return _delete_kv(path)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _set_kv(path, body):
    payload = json.loads(body) if body else {}
    key = path.split("/kv/")[-1].split("?")[0]
    _kvs[key] = {"key": key, "value": payload.get("value", ""), "last_modified": time.time()}
    return 200, {"Content-Type": "application/json"}, json.dumps(_kvs[key]).encode()

def _get_kv(path):
    key = path.split("/kv/")[-1].split("?")[0]
    kv = _kvs.get(key)
    return (200, {"Content-Type": "application/json"}, json.dumps(kv)) if kv else (404, {"Content-Type": "application/json"}, json.dumps({"error": "NotFound"}).encode())

def _list_kv(path): return 200, {"Content-Type": "application/json"}, json.dumps({"items": list(_kvs.values())}).encode()
def _delete_kv(path):
    key = path.split("/kv/")[-1].split("?")[0]
    if key in _kvs: del _kvs[key]
    return 204, {}, b""

def reset(): _kvs.clear()
def get_state(): return {"kvs": copy.deepcopy(_kvs)}
