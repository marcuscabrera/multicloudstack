"""Azure DNS."""
import copy, json, time, uuid
from ministack.core.responses import AccountScopedDict, new_uuid
_zones = AccountScopedDict()

async def handle_request(method, path, headers, body, query_params):
    if "/dnsZones/" in path and method in ("PUT", "POST"): return _create_zone(path, body)
    if "/dnsZones" in path and method == "GET": return _list_zones(path)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _create_zone(path, body):
    payload = json.loads(body) if body else {}
    name = payload.get("name", f"zone-{new_uuid()[:8]}")
    z = {"name": name, "nameServers": [f"ns{i}.azure.local" for i in range(1, 5)], "provisioningState": "Succeeded"}
    _zones[name] = z
    return 200, {"Content-Type": "application/json"}, json.dumps({"name": name, "properties": z}).encode()

def _list_zones(path): return 200, {"Content-Type": "application/json"}, json.dumps({"value": [{"name": n, "properties": z} for n, z in _zones.items()]}).encode()
def reset(): _zones.clear()
def get_state(): return {"zones": copy.deepcopy(_zones)}
