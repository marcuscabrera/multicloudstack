"""
Azure ARM Resource ID Parser.
Parses ARM Resource IDs into their components:
  /subscriptions/{sub}/resourceGroups/{rg}/providers/{provider}/{type}/{name}
  /subscriptions/{sub}/providers/{provider}/{type}/{name}
"""

import re
import logging

logger = logging.getLogger("azure_resource_id")

# ARM Resource ID pattern
_ARM_RE = re.compile(
    r"^/subscriptions/(?P<subscription>[^/]+)"
    r"(?:/resourceGroups/(?P<resource_group>[^/]+))?"
    r"(?:/providers/(?P<provider>[^/]+))?"
    r"(?P<rest>.*)?$"
)


def parse_resource_id(resource_id: str) -> dict:
    """
    Parse an ARM Resource ID into its components.

    Returns dict with keys:
        subscription_id, resource_group, provider,
        resource_type, resource_name, full_path

    Examples:
        /subscriptions/0000-0001/resourceGroups/dev-rg/providers/Microsoft.Storage/storageAccounts/myacct
        /subscriptions/0000-0001/providers/Microsoft.Compute/virtualMachines/myvm
    """
    if not resource_id:
        return {}

    # Strip trailing slash
    resource_id = resource_id.rstrip("/")

    match = _ARM_RE.match(resource_id)
    if not match:
        return {"raw": resource_id}

    result = {
        "subscription_id": match.group("subscription"),
        "resource_group": match.group("resource_group"),
        "provider": match.group("provider"),
        "raw": resource_id,
    }

    # Parse the rest into type/name pairs
    rest = match.group("rest") or ""
    rest = rest.strip("/")
    if rest:
        parts = rest.split("/")
        # Even indices are types, odd indices are names
        types = []
        names = []
        for i in range(0, len(parts), 2):
            types.append(parts[i])
            if i + 1 < len(parts):
                names.append(parts[i + 1])

        if types:
            # Build full resource type (e.g., "Microsoft.Storage/storageAccounts")
            if result.get("provider"):
                result["resource_type"] = f"{result['provider']}/{types[0]}"
            else:
                result["resource_type"] = types[0] if types else ""
            result["resource_name"] = names[0] if names else ""

        if len(types) > 1:
            result["child_type"] = types[-1]
            result["child_name"] = names[-1] if len(names) > len(types) - 1 else ""

    result["full_path"] = rest
    return result


def build_resource_id(subscription_id: str, resource_group: str,
                      provider: str, resource_type: str,
                      resource_name: str, api_version: str = None) -> str:
    """Build an ARM Resource ID string."""
    rid = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/{provider}/{resource_type}/{resource_name}"
    if api_version:
        rid += f"?api-version={api_version}"
    return rid


def extract_api_version(query_string: str) -> str:
    """Extract api-version from query string."""
    if not query_string:
        return ""
    for param in query_string.split("&"):
        if param.startswith("api-version="):
            return param.split("=", 1)[1]
    return ""


def extract_subscription_id(path: str, headers: dict = None) -> str:
    """Extract subscription ID from path or headers."""
    from ministack.core.auth_azure import AZURE_SUBSCRIPTION_ID
    parts = path.strip("/").split("/")
    for i, p in enumerate(parts):
        if p == "subscriptions" and i + 1 < len(parts):
            return parts[i + 1]
    if headers:
        return headers.get("x-ms-subscription-id", AZURE_SUBSCRIPTION_ID)
    return AZURE_SUBSCRIPTION_ID


def extract_resource_group(path: str) -> str:
    """Extract resource group name from path."""
    from ministack.core.auth_azure import AZURE_RESOURCE_GROUP
    parts = path.strip("/").split("/")
    for i, p in enumerate(parts):
        if p == "resourceGroups" and i + 1 < len(parts):
            return parts[i + 1]
    return AZURE_RESOURCE_GROUP
