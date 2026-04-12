"""Azure Event Hubs — streaming."""
import copy, json, time, uuid
from ministack.core.responses import AccountScopedDict, new_uuid
_hubs = AccountScopedDict()
_events = []

async def handle_request(method, path, headers, body, query_params):
    if "/eventhubs/" in path and method in ("PUT", "POST"): return _create_hub(path, body)
    if "/eventhubs" in path and method == "GET": return _list_hubs(path)
    if "/messages" in path and method == "POST": return _send_event(path, body)
    if "/messages" in path and method == "GET": return _receive_events(path)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _create_hub(path, body):
    payload = json.loads(body) if body else {}
    name = payload.get("name", f"hub-{new_uuid()[:8]}")
    hub = {"name": name, "partitionCount": payload.get("partitionCount", 4), "status": "Active"}
    _hubs[name] = hub
    return 200, {"Content-Type": "application/json"}, json.dumps({"name": name, "properties": hub}).encode()

def _list_hubs(path): return 200, {"Content-Type": "application/json"}, json.dumps({"value": [{"name": n, "properties": h} for n, h in _hubs.items()]}).encode()

def _send_event(path, body):
    msg = {"messageId": new_uuid(), "body": body.decode() if body else "", "enqueued": time.time()}
    _events.append(msg)
    return 201, {"Content-Type": "application/json"}, json.dumps(msg).encode()

def _receive_events(path):
    if _events:
        msg = _events.pop(0)
        return 200, {"Content-Type": "application/json"}, json.dumps(msg).encode()
    return 204, {}, b""

def reset(): _hubs.clear(); _events.clear()
def get_state(): return {"hubs": copy.deepcopy(_hubs)}
