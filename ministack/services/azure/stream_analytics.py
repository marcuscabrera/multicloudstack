"""Azure Stream Analytics."""
import copy, json, time, uuid
from ministack.core.responses import AccountScopedDict, new_uuid
_jobs = AccountScopedDict()

async def handle_request(method, path, headers, body, query_params):
    if "/streamingjobs/" in path and method in ("PUT", "POST"): return _create_job(path, body)
    if "/streamingjobs" in path and method == "GET": return _list_jobs(path)
    if "/start" in path and method == "POST": return _start_job(path)
    if "/stop" in path and method == "POST": return _stop_job(path)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _create_job(path, body):
    payload = json.loads(body) if body else {}
    name = payload.get("name", f"stream-{new_uuid()[:8]}")
    j = {"name": name, "state": "Created", "outputStartMode": "JobStartTime"}
    _jobs[name] = j
    return 200, {"Content-Type": "application/json"}, json.dumps({"name": name, "properties": j}).encode()

def _list_jobs(path): return 200, {"Content-Type": "application/json"}, json.dumps({"value": [{"name": n, "properties": j} for n, j in _jobs.items()]}).encode()
def _start_job(path):
    name = path.split("/streamingjobs/")[1].split("/")[0]
    if name in _jobs: _jobs[name]["state"] = "Running"
    return 200, {"Content-Type": "application/json"}, b"{}"
def _stop_job(path):
    name = path.split("/streamingjobs/")[1].split("/")[0]
    if name in _jobs: _jobs[name]["state"] = "Stopped"
    return 200, {"Content-Type": "application/json"}, b"{}"
def reset(): _jobs.clear()
def get_state(): return {"jobs": copy.deepcopy(_jobs)}
