"""Azure AD B2C — authentication."""
import json, time, uuid
from ministack.core.auth_azure import issue_token

async def handle_request(method, path, headers, body, query_params):
    if "/oauth2" in path and method == "POST":
        form = {}
        if body:
            for p in body.decode().split("&"):
                if "=" in p: k, v = p.split("=", 1); form[k] = v
        token = issue_token(client_id=form.get("client_id"), scope=form.get("scope", "openid"))
        return (200, {"Content-Type": "application/json"}, json.dumps(token)) if token else (401, {"Content-Type": "application/json"}, json.dumps({"error": "invalid_client"}).encode())
    return 404, {"Content-Type": "application/json"}, json.dumps({"error": "Not found"}).encode()

def reset(): pass
def get_state(): return {}
