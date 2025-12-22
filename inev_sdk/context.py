"""Context manager for tracking state transitions."""

from typing import Optional

from .client import INEVClient
from .decorators import _get_global_client


class InstrumentationContext:
    """Context manager for tracking state transitions."""

    def __init__(
        self,
        entity: str,
        record_id: Optional[str] = None,
        from_state: Optional[str] = None,
        action: str = "state_transition",
        client: Optional[INEVClient] = None,
    ):
        self.entity = entity
        self.record_id = record_id
        self.from_state = from_state
        self.action = action
        self._client = client or _get_global_client()
        self.to_state: Optional[str] = None
        self.outcome = "success"
        self.error_message: Optional[str] = None

    def set_to_state(self, state: str):
        """Set the target state."""
        self.to_state = state

    def set_record_id(self, record_id: str):
        """Set the record ID (if not known at context creation)."""
        self.record_id = record_id

    def set_error(self, message: str):
        """Mark as error."""
        self.outcome = "error"
        self.error_message = message

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.outcome = "error"
            self.error_message = str(exc_val)

        await self._client.emit(
            entity=self.entity,
            action=self.action,
            record_id=self.record_id,
            from_state=self.from_state,
            to_state=self.to_state,
            outcome=self.outcome,
            error_message=self.error_message,
        )
