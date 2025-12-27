"""Decorator helpers for automatic event emission."""

import functools
from collections.abc import Callable

from .client import INEVClient


def emit_domain_event(
    entity: str,
    action: str,
    record_id_attr: str | None = None,
    state_attr: str | None = None,
    client: INEVClient | None = None,
):
    """Decorator to auto-emit domain events after function execution."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            _client = client or _get_global_client()

            result = await func(*args, **kwargs)

            record_id = None
            to_state = None

            if result and record_id_attr:
                record_id = str(getattr(result, record_id_attr, None))
            if result and state_attr:
                to_state = getattr(result, state_attr, None)

            await _client.emit(
                entity=entity,
                action=action,
                record_id=record_id,
                to_state=to_state,
            )

            return result

        return wrapper

    return decorator


# Global client management
_global_client: INEVClient | None = None


def configure(api_key: str, **kwargs):
    """Configure global INEV client."""
    global _global_client
    _global_client = INEVClient(api_key, **kwargs)


def _get_global_client() -> INEVClient:
    if _global_client is None:
        raise RuntimeError("INEV SDK not configured. Call inev_sdk.configure(api_key=...) first.")
    return _global_client
