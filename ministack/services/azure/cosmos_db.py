"""
Azure Cosmos DB (NoSQL/Core SQL API).
Paths: /azure/cosmos/{account}/dbs/{db}/colls/{coll}/docs
Compatible with azure-cosmos SDK.
"""

import copy, json, logging, time, uuid
from ministack.core.responses import AccountScopedDict, new_uuid

logger = logging.getLogger("azure_cosmos")
_dbs = AccountScopedDict()
_containers = AccountScopedDict()
_docs = AccountScopedDict()

async def handle_request(method, path, headers, body, query_params):
    if path.endswith("/dbs") and method in ("POST", "PUT"):
        return _create_db(body)
    if path.endswith("/dbs") and method == "GET":
        return _list_dbs()
    if "/colls" in path and method in ("POST", "PUT") and not path.endswith("/docs"):
        return _create_container(path, body)
    if "/colls" in path and method == "GET" and not path.endswith("/docs"):
        return _list_containers(path)
    if path.endswith("/docs") and method in ("POST", "PUT"):
        return _create_doc(path, body)
    if path.endswith("/docs") and method == "GET":
        return _list_docs(path)
    if "/docs/" in path and method == "GET":
        return _get_doc(path)
    if "/docs/" in path and method in ("DELETE", "PUT"):
        return _delete_doc(path)
    if headers.get("x-ms-documentdb-isquery") == "true" and path.endswith("/docs"):
        return _query_docs(path, body)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _create_db(body):
    payload = json.loads(body) if body else {}
    db_id = payload.get("id", f"db-{new_uuid()[:8]}")
    db = {"id": db_id, "_rid": new_uuid(), "_ts": int(time.time()), "status": "active"}
    _dbs[db_id] = db
    return 201, _cosmos_headers(), json.dumps(db).encode()

def _list_dbs():
    return 200, _cosmos_headers(), json.dumps({"Databases": [{"id": d["id"]} for d in _dbs.values()]}).encode()

def _create_container(path, body):
    payload = json.loads(body) if body else {}
    coll_id = payload.get("id", f"coll-{new_uuid()[:8]}")
    coll = {"id": coll_id, "_rid": new_uuid(), "partitionKey": payload.get("partitionKey", {}), "status": "active"}
    _containers[coll_id] = coll
    return 201, _cosmos_headers(), json.dumps(coll).encode()

def _list_containers(path):
    return 200, _cosmos_headers(), json.dumps({"DocumentCollections": list(_containers.values())}).encode()

def _create_doc(path, body):
    payload = json.loads(body) if body else {}
    doc_id = payload.get("id", new_uuid())
    payload["id"] = doc_id
    _docs[doc_id] = payload
    return 201, _cosmos_headers(), json.dumps(payload).encode()

def _list_docs(path):
    return 200, _cosmos_headers(), json.dumps({"Documents": list(_docs.values())}).encode()

def _get_doc(path):
    doc_id = path.rsplit("/docs/", 1)[-1].split("?")[0].split("/")[0]
    doc = _docs.get(doc_id)
    if not doc: return 404, _cosmos_headers(), json.dumps({"error": "NotFound"}).encode()
    return 200, _cosmos_headers(), json.dumps(doc).encode()

def _delete_doc(path):
    doc_id = path.rsplit("/docs/", 1)[-1].split("?")[0].split("/")[0]
    if doc_id in _docs: del _docs[doc_id]
    return 204, {}, b""

def _query_docs(path, body):
    payload = json.loads(body) if body else {}
    query = payload.get("query", "")
    return 200, _cosmos_headers(), json.dumps({"Documents": list(_docs.values()), "_query": query}).encode()

def _cosmos_headers():
    return {"Content-Type": "application/json", "x-ms-request-charge": "1.0", "x-ms-resource-usage": "documentSize=1;documentsSize=1"}

def reset():
    _dbs.clear()
    _containers.clear()
    _docs.clear()

def get_state():
    return {"dbs": copy.deepcopy(_dbs), "containers": copy.deepcopy(_containers), "docs": copy.deepcopy(_docs)}
