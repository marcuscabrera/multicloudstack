"""
Azure Key Vault Secrets.
Paths: /keyvault/{vault}/secrets/{name}[/{version}]
Compatible with azure-keyvault-secrets SDK.
"""

import copy, json, logging, time, uuid
from ministack.core.responses import AccountScopedDict, new_uuid

logger = logging.getLogger("azure_kv_secrets")
_vaults = AccountScopedDict()
_secrets = AccountScopedDict()

async def handle_request(method, path, headers, body, query_params):
    if "/secrets/" in path and method in ("PUT", "POST"):
        return _set_secret(path, body)
    if "/secrets/" in path and method == "GET":
        parts = path.split("/secrets/")
        name = parts[1].split("/")[0]
        return _get_secret(name, path)
    if path.endswith("/secrets") and method == "GET":
        return _list_secrets(path)
    if "/secrets/" in path and method == "DELETE":
        name = path.split("/secrets/")[1].split("/")[0].split("?")[0]
        return _delete_secret(name)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _vault_name(path):
    if path.startswith("/keyvault/"):
        return path.split("/keyvault/")[1].split("/")[0]
    return "default"

def _set_secret(path, body):
    payload = json.loads(body) if body else {}
    name = path.split("/secrets/")[1].split("/")[0].split("?")[0]
    vault = _vault_name(path)
    version = new_uuid()[:8]
    secret = {"id": f"/keyvault/{vault}/secrets/{name}/{version}", "value": payload.get("value", ""),
              "attributes": {"enabled": True, "created": int(time.time()), "updated": int(time.time())},
              "tags": payload.get("tags", {}), "version": version}
    _secrets[f"{vault}:{name}"] = secret
    if vault not in _vaults: _vaults[vault] = {"name": vault, "secrets": []}
    if name not in _vaults[vault]["secrets"]: _vaults[vault]["secrets"].append(name)
    return 200, {"Content-Type": "application/json"}, json.dumps(secret).encode()

def _get_secret(name, path):
    vault = _vault_name(path)
    secret = _secrets.get(f"{vault}:{name}")
    if not secret: return 404, {"Content-Type": "application/json"}, json.dumps({"error": "SecretNotFound"}).encode()
    return 200, {"Content-Type": "application/json"}, json.dumps(secret).encode()

def _list_secrets(path):
    vault = _vault_name(path)
    v = _vaults.get(vault, {})
    return 200, {"Content-Type": "application/json"}, json.dumps({"value": [{"id": f"/keyvault/{vault}/secrets/{n}"} for n in v.get("secrets", [])]}).encode()

def _delete_secret(name):
    vault = _vault_name("")
    key = f"{vault}:{name}"
    if key in _secrets: del _secrets[key]
    return 204, {}, b""

def reset():
    _vaults.clear()
    _secrets.clear()

def get_state():
    return {"vaults": copy.deepcopy(_vaults), "secrets": copy.deepcopy(_secrets)}
