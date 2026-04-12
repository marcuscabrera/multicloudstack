"""
Azure Monitor Metrics."""
import copy, json, time, uuid
from ministack.core.responses import AccountScopedDict, new_uuid
_metrics = AccountScopedDict()

async def handle_request(method, path, headers, body, query_params):
    if method == "POST" and path.endswith("/metrics"):
        return _publish_metrics(body)
    if method == "GET" and "/metrics" in path:
        return _get_metrics(path)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _publish_metrics(body):
    payload = json.loads(body) if body else {}
    _metrics.setdefault("default", []).append({"data": payload, "timestamp": time.time()})
    return 200, {"Content-Type": "application/json"}, b"{}"

def _get_metrics(path):
    return 200, {"Content-Type": "application/json"}, json.dumps({"value": _metrics.get("default", [])}).encode()

def reset(): _metrics.clear()
def get_state(): return {"metrics": copy.deepcopy(_metrics)}
