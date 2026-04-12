"""
Azure Functions — HTTP triggers.
Reuses lambda_runtime.py worker pool.
Paths: /api/{funcName} (invoke), /subscriptions/.../sites/{name}/functions (CRUD)
"""
import copy, json, logging, time, uuid, zipfile, io
from ministack.core.responses import AccountScopedDict, new_uuid
from ministack.core.lambda_runtime import get_or_create_worker, invalidate_worker
logger = logging.getLogger("azure_functions")
_functions = AccountScopedDict()

async def handle_request(method, path, headers, body, query_params):
    if "/functions" in path and method in ("POST", "PUT") and "/sites/" in path:
        return _create_function(path, body)
    if "/functions" in path and method == "GET" and "/sites/" in path:
        return _list_functions(path)
    if path.startswith("/api/"):
        func_name = path.split("/api/")[1].split("?")[0].split("/")[0]
        if method == "POST":
            return await _invoke_function(func_name, body, headers)
        if method == "GET":
            return await _invoke_function(func_name, b"{}", headers)
    if "/functions/" in path and method == "DELETE":
        return _delete_function(path)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _create_function(path, body):
    payload = json.loads(body) if body else {}
    name = payload.get("name", f"func-{new_uuid()[:8]}")
    func = {"name": name, "state": "Enabled", "config": payload, "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    code = payload.get("code", {})
    code_zip = _make_default_zip()
    if code.get("zip"):
        import base64; code_zip = base64.b64decode(code["zip"])
    _functions[name] = func
    _functions[f"{name}:code"] = {"zip": code_zip, "config": {"Runtime": "python", "Handler": "index.handler", "FunctionName": name, "MemorySize": 256, "FunctionArn": f"/api/{name}"}}
    return 200, {"Content-Type": "application/json"}, json.dumps(func).encode()

def _list_functions(path):
    funcs = [f for k, f in _functions.items() if ":code" not in k]
    return 200, {"Content-Type": "application/json"}, json.dumps({"value": funcs}).encode()

def _delete_function(path):
    name = path.split("/functions/")[-1].split("?")[0].split("/")[0]
    if name in _functions:
        del _functions[name]
        invalidate_worker(name)
    return 204, {}, b""

async def _invoke_function(name, body, headers):
    code_entry = _functions.get(f"{name}:code")
    if not code_entry:
        return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Function not found"}).encode()
    try:
        event = json.loads(body) if body else {}
    except: event = {}
    worker = get_or_create_worker(name, code_entry["config"], code_entry["zip"])
    result = worker.invoke(event, new_uuid())
    resp = result.get("result", "")
    if isinstance(resp, dict):
        return 200, {"Content-Type": "application/json"}, json.dumps(resp).encode()
    return 200, {"Content-Type": "application/json"}, json.dumps({"body": str(resp)}).encode()

def _make_default_zip():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("index.py", "def handler(event, context):\n    return {'statusCode': 200, 'body': 'OK'}\n")
    return buf.getvalue()

def reset():
    _functions.clear()
    from ministack.core.lambda_runtime import reset as reset_workers; reset_workers()

def get_state():
    funcs = {}
    for k, v in _functions.items():
        if ":code" in k and v.get("zip"):
            import base64; vc = dict(v); vc["zip"] = base64.b64encode(vc["zip"]).decode()
            funcs[k] = vc
        else: funcs[k] = v
    return {"functions": copy.deepcopy(funcs)}
