"""Azure Event Grid."""
import copy, json, time, uuid
from ministack.core.responses import AccountScopedDict, new_uuid
_topics = AccountScopedDict()
_events = []

async def handle_request(method, path, headers, body, query_params):
    if "/topics/" in path and method in ("PUT", "POST"): return _create_topic(path, body)
    if "/topics" in path and method == "GET": return _list_topics(path)
    if "/events" in path and method == "POST": return _publish_events(path, body)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _create_topic(path, body):
    payload = json.loads(body) if body else {}
    name = payload.get("name", f"topic-{new_uuid()[:8]}")
    topic = {"name": name, "endpoint": f"http://localhost:4566/eventgrid/{name}", "status": "Active"}
    _topics[name] = topic
    return 200, {"Content-Type": "application/json"}, json.dumps({"name": name, "properties": topic}).encode()

def _list_topics(path): return 200, {"Content-Type": "application/json"}, json.dumps({"value": [{"name": n, "properties": t} for n, t in _topics.items()]}).encode()

def _publish_events(path, body):
    payload = json.loads(body) if body else {}
    events = payload if isinstance(payload, list) else [payload]
    for e in events: e["id"] = new_uuid(); e["time"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _events.extend(events)
    return 200, {"Content-Type": "application/json"}, json.dumps({"status": "accepted"}).encode()

def reset(): _topics.clear(); _events.clear()
def get_state(): return {"topics": copy.deepcopy(_topics)}
