"""
FunctionGraph — Huawei Cloud serverless functions.
Based on existing Lambda implementation. Reuses lambda_runtime.py worker pool.

Paths: /v2/{project_id}/fgs/functions/...
Supports: Function CRUD, Invoke, Versions, Aliases
"""

import base64
import copy
import json
import logging
import os
import time

from ministack.core.auth_huawei import HUAWEICLOUD_PROJECT_ID, HUAWEICLOUD_REGION
from ministack.core.persistence import load_state, PERSIST_STATE
from ministack.core.responses import AccountScopedDict, new_uuid
from ministack.core.lambda_runtime import get_or_create_worker, invalidate_worker

logger = logging.getLogger("functiongraph")

REGION = os.environ.get("HUAWEICLOUD_REGION", HUAWEICLOUD_REGION)
PROJECT_ID = os.environ.get("HUAWEICLOUD_PROJECT_ID", HUAWEICLOUD_PROJECT_ID)

_functions = AccountScopedDict()
_aliases = AccountScopedDict()

# ── Persistence ────────────────────────────────────────────

def get_state():
    funcs = {}
    for name, f in _functions.items():
        fc = copy.deepcopy(f)
        if fc.get("code") and isinstance(fc["code"], bytes):
            fc["code"] = base64.b64encode(fc["code"]).decode()
        funcs[name] = fc
    return {"functions": funcs, "aliases": copy.deepcopy(_aliases)}

def restore_state(data):
    if data:
        for name, f in data.get("functions", {}).items():
            if f.get("code") and isinstance(f["code"], str):
                f["code"] = base64.b64decode(f["code"])
            _functions[name] = f
        _aliases.update(data.get("aliases", {}))

_restored = load_state("functiongraph")
if _restored:
    restore_state(_restored)


def _make_function_arn(name: str) -> str:
    return f"arn:hw:functiongraph:{REGION}:{PROJECT_ID}:function:{name}"


async def handle_request(method: str, path: str, headers: dict, body: bytes, query_params: dict) -> tuple:
    """Handle FunctionGraph request."""

    # POST /v2/{proj}/fgs/functions — Create function
    if path.endswith("/fgs/functions") and method == "POST":
        return await _create_function(body, headers)

    # GET /v2/{proj}/fgs/functions — List functions
    if path.endswith("/fgs/functions") and method == "GET":
        return _list_functions()

    # GET /v2/{proj}/fgs/functions/{name} — Get function
    if "/fgs/functions/" in path and method == "GET" and not "/invocations" in path and not "/aliases" in path:
        name = path.split("/fgs/functions/")[1].split("/")[0]
        return _get_function(name)

    # DELETE /v2/{proj}/fgs/functions/{name} — Delete function
    if "/fgs/functions/" in path and method == "DELETE" and not "/aliases" in path:
        name = path.split("/fgs/functions/")[1].split("/")[0]
        return _delete_function(name)

    # PUT /v2/{proj}/fgs/functions/{name}/code — Update function code
    if "/fgs/functions/" in path and "/code" in path and method == "PUT":
        name = path.split("/fgs/functions/")[1].split("/")[0]
        return await _update_function_code(name, body, headers)

    # POST /v2/{proj}/fgs/functions/{name}/invocations — Invoke function
    if "/fgs/functions/" in path and "/invocations" in path and method == "POST":
        name = path.split("/fgs/functions/")[1].split("/invocations")[0]
        return await _invoke_function(name, body, headers)

    # POST /v2/{proj}/fgs/functions/{name}/aliases — Create alias
    if "/fgs/functions/" in path and "/aliases" in path and method == "POST":
        func_name = path.split("/fgs/functions/")[1].split("/aliases")[0]
        return _create_alias(func_name, body)

    # GET /v2/{proj}/fgs/functions/{name}/aliases — List aliases
    if "/fgs/functions/" in path and "/aliases" in path and method == "GET":
        func_name = path.split("/fgs/functions/")[1].split("/aliases")[0]
        return _list_aliases(func_name)

    return 404, {"Content-Type": "application/json"}, json.dumps({
        "error_msg": "API not found", "error_code": "FGS.0001"
    }).encode()


async def _create_function(body: bytes, headers: dict) -> tuple:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return 400, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": "Invalid JSON body", "error_code": "FGS.0010"
        }).encode()

    name = payload.get("func_name", f"function-{new_uuid()[:8]}")
    if name in _functions:
        return 409, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"Function already exists: {name}", "error_code": "FGS.0011"
        }).encode()

    runtime = payload.get("runtime", "Python3.9")
    handler = payload.get("handler", "index.handler")
    memory = payload.get("memory_size", 256)
    timeout = payload.get("timeout", 30)

    # Extract code
    code = payload.get("code", {})
    code_zip = None
    if code.get("file"):
        code_zip = base64.b64decode(code["file"])
    elif code.get("zip_file"):
        code_zip = base64.b64decode(code["zip_file"])
    else:
        # Create minimal zip
        import zipfile, io
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("index.py", "def handler(event, context):\n    return {'statusCode': 200, 'body': 'OK'}\n")
        code_zip = buf.getvalue()

    func = {
        "func_urn": _make_function_arn(name),
        "func_name": name,
        "domain_id": "hw-domain-001",
        "namespace": PROJECT_ID,
        "project_name": PROJECT_ID,
        "package": "default",
        "runtime": runtime,
        "timeout": timeout,
        "handler": handler,
        "memory_size": memory,
        "cpu": max(256, memory),
        "code_type": "zip",
        "code_filename": f"{name}.zip",
        "code_size": len(code_zip),
        "description": payload.get("description", ""),
        "last_modified": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "version": "$LATEST",
        "image_name": None,
        "xrole": payload.get("xrole", ""),
        "app_xrole": payload.get("app_xrole", ""),
        "ephemeral_storage": payload.get("ephemeral_storage", 512),
        "custom_image": payload.get("custom_image"),
        "gpu_memory": payload.get("gpu_memory", 0),
        "gpu_type": payload.get("gpu_type", ""),
        "pre_stop_handler": payload.get("pre_stop_handler", ""),
        "pre_stop_timeout": payload.get("pre_stop_timeout", 30),
        "enterprise_project_id": payload.get("enterprise_project_id", "0"),
        "type": payload.get("type", "v2"),
    }

    _functions[name] = func
    _functions[f"{name}:code"] = {"zip": code_zip, "config": func}

    return 200, {"Content-Type": "application/json"}, json.dumps(func).encode()


def _list_functions() -> tuple:
    funcs = []
    for name, f in _functions.items():
        if ":code" not in name:
            fc = copy.deepcopy(f)
            fc.pop("code", None)
            funcs.append(fc)
    return 200, {"Content-Type": "application/json"}, json.dumps({
        "functions": funcs, "count": len(funcs)
    }).encode()


def _get_function(name: str) -> tuple:
    func = _functions.get(name)
    if not func:
        return 404, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"Function not found: {name}", "error_code": "FGS.0012"
        }).encode()
    fc = copy.deepcopy(func)
    fc.pop("code", None)
    return 200, {"Content-Type": "application/json"}, json.dumps(fc).encode()


def _delete_function(name: str) -> tuple:
    if name not in _functions:
        return 404, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"Function not found: {name}", "error_code": "FGS.0012"
        }).encode()
    del _functions[name]
    code_key = f"{name}:code"
    if code_key in _functions:
        del _functions[code_key]
    invalidate_worker(name)
    return 204, {}, b""


async def _update_function_code(name: str, body: bytes, headers: dict) -> tuple:
    if name not in _functions:
        return 404, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"Function not found: {name}", "error_code": "FGS.0012"
        }).encode()

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        payload = {}

    code = payload.get("code", {})
    code_zip = None
    if code.get("file"):
        code_zip = base64.b64decode(code["file"])
    elif code.get("zip_file"):
        code_zip = base64.b64decode(code["zip_file"])

    if code_zip:
        _functions[f"{name}:code"] = {"zip": code_zip, "config": _functions[name]}
        _functions[name]["code_size"] = len(code_zip)
        invalidate_worker(name)

    return 200, {"Content-Type": "application/json"}, json.dumps(_functions[name]).encode()


async def _invoke_function(name: str, body: bytes, headers: dict) -> tuple:
    if name not in _functions:
        return 404, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"Function not found: {name}", "error_code": "FGS.0012"
        }).encode()

    code_entry = _functions.get(f"{name}:code")
    if not code_entry:
        return 500, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": "Function code not available", "error_code": "FGS.0013"
        }).encode()

    code_zip = code_entry["zip"]
    config = code_entry["config"]

    try:
        event = json.loads(body) if body else {}
    except json.JSONDecodeError:
        event = {}

    worker = get_or_create_worker(name, config, code_zip)
    request_id = new_uuid()
    result = worker.invoke(event, request_id)

    resp_headers = {
        "Content-Type": "application/json",
        "X-Cold-Start": "true" if result.get("cold_start") else "false",
        "X-FunctionGraph-Request-Id": request_id,
    }

    if result.get("status") == "error":
        return 500, resp_headers, json.dumps({
            "errorType": type(result.get("error", "")).__name__,
            "errorMessage": result.get("error", "Unknown error"),
            "requestId": request_id,
        }).encode()

    resp_body = result.get("result", "")
    if isinstance(resp_body, dict):
        return 200, resp_headers, json.dumps(resp_body).encode()
    return 200, resp_headers, json.dumps({"result": resp_body}).encode()


def _create_alias(func_name: str, body: bytes) -> tuple:
    if func_name not in _functions:
        return 404, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"Function not found: {func_name}", "error_code": "FGS.0012"
        }).encode()

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return 400, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": "Invalid JSON", "error_code": "FGS.0010"
        }).encode()

    alias_name = payload.get("name", "")
    version = payload.get("version", "$LATEST")

    if not alias_name:
        return 400, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": "Alias name is required", "error_code": "FGS.0020"
        }).encode()

    alias_key = f"{func_name}:{alias_name}"
    alias = {
        "name": alias_name,
        "version": version,
        "func_urn": _make_function_arn(func_name),
        "additional_version_weights": payload.get("additional_version_weights", {}),
        "description": payload.get("description", ""),
        "last_modified": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _aliases[alias_key] = alias

    return 200, {"Content-Type": "application/json"}, json.dumps(alias).encode()


def _list_aliases(func_name: str) -> tuple:
    aliases = []
    prefix = f"{func_name}:"
    for key, alias in _aliases.items():
        if key.startswith(prefix):
            aliases.append(alias)
    return 200, {"Content-Type": "application/json"}, json.dumps({
        "aliases": aliases, "count": len(aliases)
    }).encode()


def reset():
    """Reset FunctionGraph state."""
    _functions.clear()
    _aliases.clear()
    from ministack.core.lambda_runtime import reset as reset_workers
    reset_workers()
