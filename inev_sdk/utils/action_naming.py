"""
Semantic action name generation from HTTP paths.

This module provides utilities for generating human-readable action names
from HTTP method and path combinations. It handles path parameters intelligently,
singularizes resource names, and creates semantic names like:

- POST /api/workspaces/{id}/members → post_workspace_members
- DELETE /api/projects/{id}/members/{member_id} → delete_project_member
- GET /api/workspaces/{id}/projects → get_workspace_projects
- PATCH /api/orders/{id}/status → patch_order_status

Algorithm:
1. Remove /api prefix and version segments (v1, v2, etc.)
2. Split path into segments
3. Filter out UUID/ID parameter segments
4. Singularize resource names where followed by ID parameter
5. Join remaining segments: {method}_{segment1}_{segment2}...
"""

import re


# Regex patterns for identifying ID segments
UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
NUMERIC_ID_PATTERN = re.compile(r"^\d+$")
# Prefixed IDs like ws_123, proj_abc, usr_xyz - prefix of 2-10 chars followed by underscore and alphanumeric
PREFIXED_ID_PATTERN = re.compile(r"^[a-z]{1,10}_[a-z0-9]+$", re.IGNORECASE)


def is_id_segment(segment: str) -> bool:
    """Check if a path segment is an ID parameter.

    Args:
        segment: Path segment to check

    Returns:
        True if segment appears to be an ID (UUID, numeric, prefixed ID, or placeholder)
    """
    if not segment:
        return True

    # Check for placeholder parameters like {id}, {user_id}
    if segment.startswith("{") and segment.endswith("}"):
        return True

    # Check for common ID patterns
    if UUID_PATTERN.match(segment):
        return True

    if NUMERIC_ID_PATTERN.match(segment):
        return True

    if PREFIXED_ID_PATTERN.match(segment):
        return True

    return False


def singularize(word: str) -> str:
    """Convert plural word to singular using simple heuristics.

    This is a lightweight singularization that handles common cases
    without requiring external dependencies like inflect.

    Args:
        word: Potentially plural word

    Returns:
        Singular form of word
    """
    # Don't singularize very short words
    if len(word) <= 2:
        return word

    # Preserve words that don't change or are already singular
    if word.endswith(("ss", "us", "is", "ous")):
        return word

    # Handle -ies -> -y (e.g., categories -> category)
    if word.endswith("ies") and len(word) > 3:
        return word[:-3] + "y"

    # Handle -es for words ending in s, x, z, ch, sh (e.g., boxes -> box, statuses -> status)
    if word.endswith("es") and len(word) > 4:
        # Check for -shes, -ches, -xes, -zes, -ses
        if word[-4:-2] in ("sh", "ch") or word[-3] in "xzs":
            return word[:-2]

    # Handle -s for regular plurals (e.g., users -> user, orders -> order)
    if word.endswith("s") and not word.endswith("ss") and len(word) > 2:
        return word[:-1]

    return word


def generate_action_name(method: str, path: str) -> str:
    """Generate semantic action name from HTTP method and path.

    Examples:
        POST /api/workspaces/{id}/members → post_workspace_members
        DELETE /api/projects/{id}/members/{member_id} → delete_project_member
        GET /api/workspaces/{id}/projects → get_workspace_projects
        PATCH /api/orders/{id}/status → patch_order_status
        GET /api/v1/users → get_users
        POST /api/v2/workspaces → post_workspaces

    Args:
        method: HTTP method (GET, POST, PATCH, DELETE, etc.)
        path: URL path (e.g., "/api/workspaces/123/members")

    Returns:
        Semantic action name (e.g., "post_workspace_members")
    """
    # Normalize method to lowercase
    method = method.lower()

    # Remove trailing slash
    path = path.rstrip("/")

    # Split path into parts
    parts = [p for p in path.split("/") if p]

    # Remove 'api' prefix and version segments (v1, v2, etc.)
    filtered_parts = []
    for part in parts:
        if part == "api":
            continue
        if re.match(r"^v\d+$", part):
            continue
        filtered_parts.append(part)

    if not filtered_parts:
        return f"{method}_root"

    # Build semantic segments
    semantic_segments: list[str] = []

    for i, segment in enumerate(filtered_parts):
        # Skip ID segments
        if is_id_segment(segment):
            continue

        # Check if the next segment is an ID (need to singularize this one)
        next_is_id = False
        if i + 1 < len(filtered_parts):
            next_is_id = is_id_segment(filtered_parts[i + 1])

        # Singularize if followed by an ID
        if next_is_id:
            semantic_segments.append(singularize(segment))
        else:
            semantic_segments.append(segment)

    # Handle case where all segments were IDs
    if not semantic_segments:
        # Return first non-ID segment singularized, or "resource"
        for segment in filtered_parts:
            if not is_id_segment(segment):
                return f"{method}_{singularize(segment)}"
        return f"{method}_resource"

    # Join segments
    resource_path = "_".join(semantic_segments)

    return f"{method}_{resource_path}"


def generate_semantic_action_name(method: str, path: str) -> str:
    """Generate semantic action name using verb mapping for common REST patterns.

    This is an enhanced version that converts REST methods to semantic verbs:
    - POST /api/workspaces/{id}/members → add_workspace_member
    - DELETE /api/projects/{id}/members/{member_id} → remove_project_member
    - GET /api/workspaces/{id}/projects → list_workspace_projects
    - PATCH /api/orders/{id}/status → update_order_status
    - PUT /api/users/{id} → update_user

    Args:
        method: HTTP method (GET, POST, PATCH, DELETE, etc.)
        path: URL path

    Returns:
        Semantic action name with verb
    """
    # First generate the base action name
    base_action = generate_action_name(method, path)

    # Split to get method and resource
    parts = base_action.split("_", 1)
    if len(parts) != 2:
        return base_action

    method_prefix, resource = parts

    # Determine if this is a collection operation (plural) or single resource
    is_collection = resource.endswith("s") and not resource.endswith("ss")

    # Map HTTP methods to semantic verbs
    verb_mapping = {
        "get": "list" if is_collection else "get",
        "post": "add" if "_" in resource else "create",
        "patch": "update",
        "put": "update",
        "delete": "remove" if "_" in resource else "delete",
    }

    verb = verb_mapping.get(method_prefix, method_prefix)

    return f"{verb}_{resource}"
