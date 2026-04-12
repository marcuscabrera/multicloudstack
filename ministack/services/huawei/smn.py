"""
SMN (Simple Message Notification) — Huawei Cloud compatible.
Based on existing SNS implementation.

Paths: /v2/{project_id}/notifications/...
Supports: Topic CRUD, Publish, Subscribe, Unsubscribe, ListSubscriptions
"""

import copy
import json
import logging
import os
import time
from urllib.parse import parse_qs

from ministack.core.auth_huawei import HUAWEICLOUD_PROJECT_ID, HUAWEICLOUD_REGION
from ministack.core.persistence import load_state, PERSIST_STATE
from ministack.core.responses import AccountScopedDict, get_account_id, new_uuid

logger = logging.getLogger("smn")

REGION = os.environ.get("HUAWEICLOUD_REGION", HUAWEICLOUD_REGION)
PROJECT_ID = os.environ.get("HUAWEICLOUD_PROJECT_ID", HUAWEICLOUD_PROJECT_ID)

_topics = AccountScopedDict()
_subscriptions = AccountScopedDict()
_messages: list = []  # Published messages log

# ── Persistence ────────────────────────────────────────────

def get_state():
    return {"topics": copy.deepcopy(_topics), "subscriptions": copy.deepcopy(_subscriptions)}

def restore_state(data):
    if data:
        _topics.update(data.get("topics", {}))
        _subscriptions.update(data.get("subscriptions", {}))

_restored = load_state("smn")
if _restored:
    restore_state(_restored)


def _make_topic_arn(name: str) -> str:
    return f"arn:hw:smn:{REGION}:{PROJECT_ID}:{name}"


def _extract_project_id(path: str) -> str:
    parts = path.strip("/").split("/")
    for i, p in enumerate(parts):
        if (p.startswith("v") and i + 1 < len(parts)):
            return parts[i + 1]
    return PROJECT_ID


async def handle_request(method: str, path: str, headers: dict, body: bytes, query_params: dict) -> tuple:
    """Handle SMN request."""
    project_id = _extract_project_id(path)

    # Parse JSON body if present
    payload = {}
    if body and headers.get("content-type", "").startswith("application/json"):
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            pass

    # Route by path
    if path.endswith("/topics") and method == "POST":
        return _create_topic(payload, project_id)
    if "/topics/" in path and method == "GET" and not path.endswith("/subscriptions"):
        topic_name = path.split("/topics/")[1].split("/")[0]
        return _get_topic(topic_name, project_id)
    if "/topics/" in path and method == "DELETE":
        topic_name = path.split("/topics/")[1].split("/")[0]
        return _delete_topic(topic_name, project_id)
    if path.endswith("/topics") and method == "GET":
        return _list_topics(project_id)
    if "/topics/" in path and "/publish" in path and method == "POST":
        topic_name = path.split("/topics/")[1].split("/")[0]
        return _publish(topic_name, payload, project_id)
    if "/topics/" in path and "/subscriptions" in path and method == "POST":
        topic_name = path.split("/topics/")[1].split("/subscriptions")[0]
        return _subscribe(topic_name, payload, project_id)
    if path.endswith("/subscriptions") and method == "GET":
        return _list_subscriptions(project_id)
    if "/subscriptions/" in path and method == "DELETE":
        sub_id = path.split("/subscriptions/")[-1]
        return _unsubscribe(sub_id)

    return 404, {"Content-Type": "application/json"}, json.dumps({
        "error_msg": "API not found", "error_code": "SMN.0001"
    }).encode()


def _create_topic(payload: dict, project_id: str) -> tuple:
    name = payload.get("name", f"topic-{new_uuid()[:8]}")
    display_name = payload.get("display_name", "")

    if name in _topics:
        return 409, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"Topic already exists: {name}", "error_code": "SMN.0010"
        }).encode()

    arn = _make_topic_arn(name)
    topic = {
        "topic_urn": arn,
        "name": name,
        "display_name": display_name,
        "push_policy": 0,
        "update_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "create_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _topics[name] = topic

    return 200, {"Content-Type": "application/json"}, json.dumps({
        "request_id": new_uuid(),
        "topic_urn": arn,
    }).encode()


def _list_topics(project_id: str) -> tuple:
    topics = [_topics[n] for n in _topics.keys()]
    return 200, {"Content-Type": "application/json"}, json.dumps({
        "topics": topics,
        "request_id": new_uuid(),
    }).encode()


def _get_topic(name: str, project_id: str) -> tuple:
    topic = _topics.get(name)
    if not topic:
        return 404, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"Topic not found: {name}", "error_code": "SMN.0011"
        }).encode()
    return 200, {"Content-Type": "application/json"}, json.dumps({
        "topic": topic, "request_id": new_uuid()
    }).encode()


def _delete_topic(name: str, project_id: str) -> tuple:
    if name not in _topics:
        return 404, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"Topic not found: {name}", "error_code": "SMN.0011"
        }).encode()
    del _topics[name]
    return 200, {"Content-Type": "application/json"}, json.dumps({
        "request_id": new_uuid()
    }).encode()


def _publish(name: str, payload: dict, project_id: str) -> tuple:
    if name not in _topics:
        return 404, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"Topic not found: {name}", "error_code": "SMN.0011"
        }).encode()

    message = payload.get("message", "")
    subject = payload.get("subject", "")
    msg_id = new_uuid()

    record = {
        "message_id": msg_id,
        "topic_urn": _topics[name]["topic_urn"],
        "message": message,
        "subject": subject,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _messages.append(record)

    # Fan-out to subscriptions
    for sub in _subscriptions.values():
        if sub["topic_urn"] == _topics[name]["topic_urn"]:
            # Store delivered message for the subscription
            sub.setdefault("delivered_messages", []).append(msg_id)

    return 200, {"Content-Type": "application/json"}, json.dumps({
        "request_id": new_uuid(),
        "message_id": msg_id,
    }).encode()


def _subscribe(topic_name: str, payload: dict, project_id: str) -> tuple:
    if topic_name not in _topics:
        return 404, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"Topic not found: {topic_name}", "error_code": "SMN.0011"
        }).encode()

    endpoint = payload.get("endpoint", "")
    protocol = payload.get("protocol", "email")

    if not endpoint:
        return 400, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": "Endpoint is required", "error_code": "SMN.0020"
        }).encode()

    sub_id = new_uuid()
    sub = {
        "subscription_urn": f"{_topics[topic_name]['topic_urn']}:{sub_id}",
        "topic_urn": _topics[topic_name]["topic_urn"],
        "endpoint": endpoint,
        "protocol": protocol,
        "status": "confirmed",
        "owner": PROJECT_ID,
    }
    _subscriptions[sub_id] = sub

    return 200, {"Content-Type": "application/json"}, json.dumps({
        "request_id": new_uuid(),
        "subscription_urn": sub["subscription_urn"],
    }).encode()


def _list_subscriptions(project_id: str) -> tuple:
    subs = list(_subscriptions.values())
    return 200, {"Content-Type": "application/json"}, json.dumps({
        "subscriptions": subs,
        "request_id": new_uuid(),
    }).encode()


def _unsubscribe(sub_id: str) -> tuple:
    if sub_id not in _subscriptions:
        return 404, {"Content-Type": "application/json"}, json.dumps({
            "error_msg": f"Subscription not found: {sub_id}", "error_code": "SMN.0021"
        }).encode()
    del _subscriptions[sub_id]
    return 200, {"Content-Type": "application/json"}, json.dumps({
        "request_id": new_uuid()
    }).encode()


def reset():
    """Reset SMN state."""
    _topics.clear()
    _subscriptions.clear()
    _messages.clear()
