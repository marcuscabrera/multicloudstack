"""Azure Communication Services — Email."""
import copy, json, time, uuid
from ministack.core.responses import AccountScopedDict, new_uuid
_emails = []

async def handle_request(method, path, headers, body, query_params):
    if "/emails:send" in path and method == "POST": return _send_email(path, body)
    if "/emails" in path and method == "GET": return _list_emails(path)
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def _send_email(path, body):
    payload = json.loads(body) if body else {}
    email = {"messageId": new_uuid(), "to": payload.get("recipients", {}).get("to", []), "subject": payload.get("content", {}).get("subject", ""), "status": "sent", "sentAt": time.time()}
    _emails.append(email)
    return 202, {"Content-Type": "application/json"}, json.dumps({"id": email["messageId"], "status": "sent"}).encode()

def _list_emails(path): return 200, {"Content-Type": "application/json"}, json.dumps({"value": _emails}).encode()
def reset(): _emails.clear()
def get_state(): return {"emails": copy.deepcopy(_emails)}
