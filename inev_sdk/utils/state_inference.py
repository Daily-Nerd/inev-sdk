"""
State inference from HTTP context.

Provides zero-config state inference from HTTP method and status code
combinations. Uses standard REST conventions to determine the resulting
state of an operation.

State Mapping:
    POST + 201 → "created"
    POST + 200 → "processed" (non-creation POST like action endpoints)
    PUT + 200/204 → "updated"
    PATCH + 200/204 → "updated"
    DELETE + 200/204 → "deleted"
    GET + 200 → None (reads don't change state)
    * + 4xx/5xx → None (errors handled via outcome field)
"""

from __future__ import annotations


def infer_state_from_http(
    method: str,
    status_code: int,
    action: str | None = None,
) -> str | None:
    """Infer to_state from HTTP method and status code.

    Uses REST conventions to determine the resulting state of an operation.
    Only infers state for successful write operations.

    Args:
        method: HTTP method (GET, POST, PUT, PATCH, DELETE)
        status_code: HTTP response status code
        action: Optional action name for additional context

    Returns:
        Inferred state name, or None if state cannot be determined.

    Examples:
        >>> infer_state_from_http("POST", 201)
        "created"

        >>> infer_state_from_http("PUT", 200)
        "updated"

        >>> infer_state_from_http("DELETE", 204)
        "deleted"

        >>> infer_state_from_http("GET", 200)
        None  # Reads don't change state

        >>> infer_state_from_http("POST", 500)
        None  # Errors handled via outcome
    """
    method = method.upper()

    # Don't infer state for error responses (4xx, 5xx)
    if status_code >= 400:
        return None

    # Don't infer state for redirects (3xx)
    if status_code >= 300:
        return None

    # GET requests don't change state
    if method == "GET":
        return None

    # HEAD and OPTIONS don't change state
    if method in ("HEAD", "OPTIONS"):
        return None

    # POST - typically creates, but could be action endpoint
    if method == "POST":
        if status_code == 201:
            return "created"
        if status_code == 200:
            # POST with 200 could be many things - check action for hints
            if action:
                return _infer_state_from_action(action)
            return "processed"
        if status_code == 202:
            return "pending"  # Accepted for async processing
        return None

    # PUT - replaces/updates resource
    if method == "PUT":
        if status_code in (200, 204):
            return "updated"
        if status_code == 201:
            return "created"  # PUT can create if resource doesn't exist
        return None

    # PATCH - partial update
    if method == "PATCH":
        if status_code in (200, 204):
            # Check if action gives more specific state
            if action:
                inferred = _infer_state_from_action(action)
                if inferred:
                    return inferred
            return "updated"
        return None

    # DELETE - removes resource
    if method == "DELETE":
        if status_code in (200, 204):
            return "deleted"
        if status_code == 202:
            return "deleting"  # Async deletion
        return None

    return None


def _infer_state_from_action(action: str) -> str | None:
    """Infer state from action name patterns.

    Looks for common verb prefixes in action names to determine state.

    Args:
        action: Action name (e.g., "post_order_confirm", "patch_user_activate")

    Returns:
        Inferred state or None
    """
    if not action:
        return None

    action_lower = action.lower()

    # Check for state-changing verbs in the action name
    state_verbs = {
        "confirm": "confirmed",
        "approve": "approved",
        "reject": "rejected",
        "cancel": "cancelled",
        "archive": "archived",
        "activate": "activated",
        "deactivate": "deactivated",
        "suspend": "suspended",
        "resume": "resumed",
        "complete": "completed",
        "submit": "submitted",
        "publish": "published",
        "unpublish": "unpublished",
        "verify": "verified",
        "enable": "enabled",
        "disable": "disabled",
        "start": "started",
        "stop": "stopped",
        "pause": "paused",
        "ship": "shipped",
        "deliver": "delivered",
        "refund": "refunded",
        "expire": "expired",
        "renew": "renewed",
        "upgrade": "upgraded",
        "downgrade": "downgraded",
    }

    # Sort by verb length (longest first) to handle overlapping verbs
    # e.g., "deactivate" must be checked before "activate"
    for verb, state in sorted(state_verbs.items(), key=lambda x: len(x[0]), reverse=True):
        if verb in action_lower:
            return state

    return None


def infer_from_state_by_method(method: str) -> str | None:
    """Infer from_state based on HTTP method semantics.

    For certain methods, we can infer what state the resource was likely in
    before the operation.

    Args:
        method: HTTP method

    Returns:
        Inferred from_state or None

    Note:
        This is less reliable than to_state inference and should be used
        with caution. State tracking is more accurate for from_state.
    """
    method = method.upper()

    # DELETE implies resource existed (was in some active state)
    if method == "DELETE":
        return "active"  # Generic "was active before deletion"

    # Can't reliably infer from_state for other methods
    return None
