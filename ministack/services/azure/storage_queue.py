"""Azure Storage Queue."""
import copy, json, time, uuid
from ministack.core.responses import AccountScopedDict, new_uuid
_queues = AccountScopedDict()
_messages = []

async def handle_request(method, path, headers, body, query_params):
    if path.endswith("/messages") and method == "POST": return _send_message(path, body)
    if path.endswith("/messages") and method == "GET": return _receive_message(path)
    if "/queues/" in path and method in ("PUT", "POST"): return _create_queue(path, body)
    if "/queues" in path and method == "GET": return _list_queues(path)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _create_queue(path, body):
    name = path.strip("/").split("/")[-1]
    _queues[name] = {"name": name, "created": time.time()}
    return 201, {"Content-Type": "application/json"}, b""

def _list_queues(path): return 200, {"Content-Type": "application/json"}, json.dumps({"value": [{"name": n} for n in _queues]}).encode()
def _send_message(path, body):
    msg = {"messageId": new_uuid(), "body": body.decode() if body else "", "insertionTime": time.time()}
    _messages.append(msg)
    return 201, {"Content-Type": "application/json"}, json.dumps(msg).encode()
def _receive_message(path):
    if _messages: return 200, {"Content-Type": "application/json"}, json.dumps({"messages": [_messages.pop(0)]}).encode()
    return 204, {}, b""

def reset(): _queues.clear(); _messages.clear()
def get_state(): return {"queues": copy.deepcopy(_queues)}
