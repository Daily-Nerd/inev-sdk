"""
Entity and record ID extraction from URL paths.

Provides zero-config extraction of entity names and record IDs from
standard REST API URL patterns. Works without requiring explicit
event mapping configuration.

Examples:
    /api/v1/orders/123 → entity="order", record_id="123"
    /api/workspaces/ws_abc/members/usr_456 → entity="member", record_id="usr_456"
    /api/users/42/profile → entity="user", record_id="42"
    /health → entity=None, record_id=None

Algorithm:
1. Remove /api prefix and version segments (v1, v2, etc.)
2. Split path into segments
3. Identify ID segments vs resource segments
4. Entity = last resource segment (singularized)
5. Record ID = ID segment following entity, or last ID segment
"""

from __future__ import annotations

import re

from inev_sdk.utils.action_naming import is_id_segment, singularize


def extract_entity_and_record_id(path: str) -> tuple[str | None, str | None]:
    """Extract entity name and record ID from URL path using REST conventions.

    This function provides zero-config entity extraction for standard REST APIs.
    It identifies the entity (resource type) and record_id from URL structure.

    Args:
        path: URL path (e.g., "/api/v1/orders/123")

    Returns:
        Tuple of (entity, record_id). Both may be None if extraction fails.

    Examples:
        >>> extract_entity_and_record_id("/api/v1/orders/123")
        ("order", "123")

        >>> extract_entity_and_record_id("/api/workspaces/ws_abc/members/usr_456")
        ("member", "usr_456")

        >>> extract_entity_and_record_id("/api/users/42/profile")
        ("user", "42")

        >>> extract_entity_and_record_id("/health")
        (None, None)
    """
    if not path:
        return None, None

    # Remove trailing slash
    path = path.rstrip("/")

    # Split path into parts
    parts = [p for p in path.split("/") if p]

    if not parts:
        return None, None

    # Filter out 'api' prefix and version segments (v1, v2, etc.)
    filtered_parts: list[str] = []
    for part in parts:
        if part == "api":
            continue
        if re.match(r"^v\d+$", part):
            continue
        filtered_parts.append(part)

    if not filtered_parts:
        return None, None

    # Separate resource segments from ID segments
    # Build list of (segment, is_id) tuples
    segment_types: list[tuple[str, bool]] = [(seg, is_id_segment(seg)) for seg in filtered_parts]

    # Find the last resource segment (non-ID) - this is the entity
    entity: str | None = None
    entity_index: int = -1

    for i in range(len(segment_types) - 1, -1, -1):
        segment, is_id = segment_types[i]
        if not is_id:
            # Check if this resource is followed by an ID (indicates it's the entity)
            if i + 1 < len(segment_types) and segment_types[i + 1][1]:
                # Resource followed by ID - this is likely the entity
                entity = singularize(segment)
                entity_index = i
                break
            elif i == len(segment_types) - 1:
                # Last segment is a resource (no ID) - could be a collection endpoint
                # Check if there's a parent resource with ID
                for j in range(i - 1, -1, -1):
                    seg, seg_is_id = segment_types[j]
                    if not seg_is_id:
                        # Found parent resource - this might be the actual entity context
                        entity = singularize(seg)
                        entity_index = j
                        break
                if entity is None:
                    # No parent with ID found, use this segment
                    entity = singularize(segment)
                    entity_index = i
                break

    if entity is None:
        # No resource segments found (all IDs?) - can't determine entity
        return None, None

    # Find record_id - look for ID segment after entity, or nearest ID
    record_id: str | None = None

    # First, try to find an ID immediately after the entity
    if entity_index + 1 < len(segment_types):
        next_seg, next_is_id = segment_types[entity_index + 1]
        if next_is_id:
            record_id = next_seg

    # If no ID after entity, find the last ID in the path
    if record_id is None:
        for seg, is_id in reversed(segment_types):
            if is_id:
                record_id = seg
                break

    return entity, record_id


def extract_parent_entity_and_id(path: str) -> tuple[str | None, str | None]:
    """Extract parent entity and its ID from nested URL paths.

    For nested resources like /workspaces/123/members/456, this returns
    the parent entity (workspace) and its ID (123).

    Args:
        path: URL path

    Returns:
        Tuple of (parent_entity, parent_id). Both may be None.

    Examples:
        >>> extract_parent_entity_and_id("/api/workspaces/ws_123/members/usr_456")
        ("workspace", "ws_123")

        >>> extract_parent_entity_and_id("/api/orders/123")
        (None, None)  # No parent
    """
    if not path:
        return None, None

    # Remove trailing slash
    path = path.rstrip("/")

    # Split path into parts
    parts = [p for p in path.split("/") if p]

    # Filter out 'api' prefix and version segments
    filtered_parts: list[str] = []
    for part in parts:
        if part == "api":
            continue
        if re.match(r"^v\d+$", part):
            continue
        filtered_parts.append(part)

    if len(filtered_parts) < 3:
        # Need at least: parent_resource, parent_id, child_resource
        return None, None

    # Find resource-id pairs
    pairs: list[tuple[str, str]] = []
    i = 0
    while i < len(filtered_parts) - 1:
        segment = filtered_parts[i]
        next_segment = filtered_parts[i + 1]

        if not is_id_segment(segment) and is_id_segment(next_segment):
            pairs.append((singularize(segment), next_segment))
            i += 2
        else:
            i += 1

    # Return the first (parent) pair if we have at least 2 pairs
    if len(pairs) >= 2:
        return pairs[0]

    return None, None
