"""
Azure Key Vault Certificates."""
import copy, json, time, uuid
from ministack.core.responses import AccountScopedDict, new_uuid
_certs = AccountScopedDict()

async def handle_request(method, path, headers, body, query_params):
    if "/certificates/" in path and method in ("PUT", "POST"):
        return _create_cert(path, body)
    if path.endswith("/certificates") and method == "GET":
        return _list_certs(path)
    if "/certificates/" in path and method == "GET":
        return _get_cert(path)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _create_cert(path, body):
    payload = json.loads(body) if body else {}
    name = path.split("/certificates/")[1].split("/")[0].split("?")[0]
    cert = {"id": f"/certificates/{name}/{new_uuid()[:8]}", "subject": payload.get("subject", "CN=localhost"), "attributes": {"enabled": True, "created": int(time.time())}}
    _certs[name] = cert
    return 200, {"Content-Type": "application/json"}, json.dumps(cert).encode()

def _list_certs(path):
    return 200, {"Content-Type": "application/json"}, json.dumps({"value": list(_certs.values())}).encode()

def _get_cert(path):
    name = path.split("/certificates/")[1].split("/")[0].split("?")[0]
    cert = _certs.get(name)
    return (200, {"Content-Type": "application/json"}, json.dumps(cert)) if cert else (404, {"Content-Type": "application/json"}, json.dumps({"error": "CertNotFound"}).encode())

def reset(): _certs.clear()
def get_state(): return {"certs": copy.deepcopy(_certs)}
