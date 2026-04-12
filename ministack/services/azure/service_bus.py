"""
Azure Service Bus — Queues and Topics.
Based on SQS/SNS patterns.

Paths:
    PUT/GET/DELETE .../queues/{queue}
    POST .../{queue}/messages (send)
    DELETE .../{queue}/messages/head (receive+delete)
"""

import copy, json, logging, os, time, uuid
from ministack.core.azure_resource_id import extract_subscription_id, extract_resource_group
from ministack.core.responses import AccountScopedDict, new_uuid

logger = logging.getLogger("azure_service_bus")
_namespaces = AccountScopedDict()
_queues = AccountScopedDict()
_messages = []

async def handle_request(method, path, headers, body, query_params):
    if "/queues/" in path and method == "PUT":
        return _create_queue(path, body)
    if "/queues" in path and method == "GET":
        return _list_queues(path)
    if "/queues/" in path and method == "DELETE":
        return _delete_queue(path)
    if "/messages" in path and method == "POST":
        return _send_message(path, body)
    if "/messages/head" in path and method == "DELETE":
        return _receive_message(path)
    if "/topics/" in path and method == "PUT":
        return _create_topic(path, body)
    if "/topics" in path and method == "GET":
        return _list_topics(path)
    if "/topics/" in path and method == "DELETE":
        return _delete_topic(path)
    if "/subscriptions/" in path and "/topics/" in path and method == "PUT":
        return _create_subscription(path, body)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _ns_queue(path):
    parts = path.strip("/").split("/")
    ns_idx = next((i for i, p in enumerate(parts) if p == "namespaces"), -1)
    ns = parts[ns_idx + 1] if ns_idx >= 0 and ns_idx + 1 < len(parts) else "default"
    q_idx = next((i for i, p in enumerate(parts) if p == "queues"), -1)
    q = parts[q_idx + 1] if q_idx >= 0 and q_idx + 1 < len(parts) else ""
    return ns, q

def _create_queue(path, body):
    ns, q = _ns_queue(path)
    if not q: return 400, {"Content-Type": "application/json"}, b'{}'
    key = f"{ns}:{q}"
    _queues[key] = {"name": q, "namespace": ns, "status": "Active", "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    return 200, {"Content-Type": "application/json"}, json.dumps(_queues[key]).encode()

def _list_queues(path):
    return 200, {"Content-Type": "application/json"}, json.dumps({"value": list(_queues.values())}).encode()

def _delete_queue(path):
    ns, q = _ns_queue(path)
    key = f"{ns}:{q}"
    if key in _queues: del _queues[key]
    return 202, {"Content-Type": "application/json"}, b"{}"

def _send_message(path, body):
    ns, q = _ns_queue(path)
    key = f"{ns}:{q}"
    if key not in _queues:
        return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Queue not found"}).encode()
    msg = {"messageId": new_uuid(), "body": body.decode() if body else "", "enqueued": time.time(), "queue": q}
    _messages.append(msg)
    return 201, {"Content-Type": "application/json"}, json.dumps(msg).encode()

def _receive_message(path):
    ns, q = _ns_queue(path)
    key = f"{ns}:{q}"
    for i, m in enumerate(_messages):
        if m.get("queue") == q:
            _messages.pop(i)
            return 200, {"Content-Type": "application/json"}, json.dumps(m).encode()
    return 204, {}, b""

def _create_topic(path, body): return _create_queue(path, body)
def _list_topics(path): return _list_queues(path)
def _delete_topic(path): return _delete_queue(path)
def _create_subscription(path, body): return 200, {"Content-Type": "application/json"}, json.dumps({"name": "sub1"}).encode()

def reset():
    _queues.clear()
    _messages.clear()

def get_state():
    return {"queues": copy.deepcopy(_queues)}
