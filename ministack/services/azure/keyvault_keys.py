"""
Azure Key Vault Keys (cryptographic)."""
import copy, json, time, uuid
from ministack.core.responses import AccountScopedDict, new_uuid
_keys = AccountScopedDict()

async def handle_request(method, path, headers, body, query_params):
    if "/keys/" in path and method in ("PUT", "POST"):
        return _create_key(path, body)
    if "/keys/" in path and method == "GET":
        return _get_key(path)
    if path.endswith("/keys") and method == "GET":
        return _list_keys(path)
    if method == "POST" and "/encrypt" in path:
        return _encrypt(body)
    if method == "POST" and "/decrypt" in path:
        return _decrypt(body)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _create_key(path, body):
    payload = json.loads(body) if body else {}
    name = path.split("/keys/")[1].split("/")[0].split("?")[0]
    key = {"kid": f"/keys/{name}/{new_uuid()[:8]}", "kty": payload.get("kty", "RSA"), "key_ops": ["encrypt", "decrypt", "sign", "verify"], "attributes": {"enabled": True, "created": int(time.time())}}
    _keys[name] = key
    return 200, {"Content-Type": "application/json"}, json.dumps(key).encode()

def _get_key(path):
    name = path.split("/keys/")[1].split("/")[0].split("?")[0]
    key = _keys.get(name)
    return (200, {"Content-Type": "application/json"}, json.dumps(key)) if key else (404, {"Content-Type": "application/json"}, json.dumps({"error": "KeyNotFound"}).encode())

def _list_keys(path):
    return 200, {"Content-Type": "application/json"}, json.dumps({"value": list(_keys.values())}).encode()

def _encrypt(body): return 200, {"Content-Type": "application/json"}, json.dumps({"ciphertext": "base64stub"}).encode()
def _decrypt(body): return 200, {"Content-Type": "application/json"}, json.dumps({"plaintext": "base64stub"}).encode()

def reset(): _keys.clear()
def get_state(): return {"keys": copy.deepcopy(_keys)}
