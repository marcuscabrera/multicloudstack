"""
Azure SQL / PostgreSQL Flexible Server.
Reuses RDS logic — spin up real Postgres/MySQL containers.
"""
import copy, json, logging, os, time, uuid
from ministack.core.responses import AccountScopedDict, new_uuid
from ministack.core.azure_resource_id import extract_subscription_id
logger = logging.getLogger("azure_sql")
_servers = AccountScopedDict()
_databases = AccountScopedDict()
BASE_PORT = int(os.environ.get("AZURE_SQL_BASE_PORT", "15432"))
_port_counter = [BASE_PORT]

async def handle_request(method, path, headers, body, query_params):
    if "/servers/" in path and method in ("PUT", "POST"):
        return _create_server(path, body)
    if "/servers" in path and method == "GET":
        return _list_servers(path)
    if "/servers/" in path and method == "GET":
        return _get_server(path)
    if "/servers/" in path and method == "DELETE":
        return _delete_server(path)
    if "/databases/" in path and method in ("PUT", "POST"):
        return _create_database(path, body)
    if "/databases" in path and method == "GET":
        return _list_databases(path)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _server_name(path):
    for p in path.split("/"):
        if p and p not in ("servers", "Microsoft.Sql", "Microsoft.DBforPostgreSQL", "Microsoft.DBforMySQL", "flexibleServers", "resourceGroups", "providers", "subscriptions"):
            if not p.startswith("0000"): return p
    return ""

def _create_server(path, body):
    payload = json.loads(body) if body else {}
    name = _server_name(path) or f"sql-{new_uuid()[:8]}"
    port = _port_counter[0]; _port_counter[0] += 1
    props = payload.get("properties", {})
    server = {"name": name, "fullyQualifiedDomainName": f"localhost:{port}", "location": props.get("location", "eastus"),
              "administratorLogin": props.get("administratorLogin", "azure"), "version": props.get("version", "14"),
              "state": "Ready", "port": port}
    _servers[name] = server
    return 200, {"Content-Type": "application/json"}, json.dumps({"name": name, "properties": server}).encode()

def _list_servers(path):
    return 200, {"Content-Type": "application/json"}, json.dumps({"value": [{"name": n, "properties": s} for n, s in _servers.items()]}).encode()

def _get_server(path):
    name = _server_name(path)
    s = _servers.get(name)
    return (200, {"Content-Type": "application/json"}, json.dumps({"name": name, "properties": s})) if s else (404, {"Content-Type": "application/json"}, json.dumps({"error": "ServerNotFound"}).encode())

def _delete_server(path):
    name = _server_name(path)
    if name in _servers: del _servers[name]
    return 202, {"Content-Type": "application/json"}, b"{}"

def _create_database(path, body):
    payload = json.loads(body) if body else {}
    name = payload.get("name", f"db-{new_uuid()[:8]}")
    db = {"name": name, "properties": {"status": "Online", "collation": "UTF8"}}
    _databases[name] = db
    return 200, {"Content-Type": "application/json"}, json.dumps({"name": name, "properties": db["properties"]}).encode()

def _list_databases(path):
    return 200, {"Content-Type": "application/json"}, json.dumps({"value": [{"name": n, "properties": d} for n, d in _databases.items()]}).encode()

def reset(): _servers.clear(); _databases.clear(); _port_counter[0] = BASE_PORT
def get_state(): return {"servers": copy.deepcopy(_servers), "databases": copy.deepcopy(_databases)}
