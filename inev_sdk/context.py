"""Context manager for tracking state transitions."""

from .client import EXCEPTION_CATEGORY_MAP, INEVClient
from .decorators import _get_global_client


class InstrumentationContext:
    """Context manager for tracking state transitions with enhanced error capture.

    Automatically captures structured error information when exceptions occur:
    - error_type: Exception class name
    - error_code: From exception.error_code or exception.code attribute
    - error_details: From exception.details or exception.error_details attribute
    - error_category: Inferred from exception type
    """

    def __init__(
        self,
        entity: str,
        record_id: str | None = None,
        from_state: str | None = None,
        action: str = "state_transition",
        client: INEVClient | None = None,
    ):
        self.entity = entity
        self.record_id = record_id
        self.from_state = from_state
        self.action = action
        self._client = client or _get_global_client()
        self.to_state: str | None = None
        self.outcome = "success"
        self.error_message: str | None = None
        self.error_code: str | None = None
        self.error_type: str | None = None
        self.error_category: str | None = None
        self.error_details: dict | None = None

    def set_to_state(self, state: str):
        """Set the target state."""
        self.to_state = state

    def set_record_id(self, record_id: str):
        """Set the record ID (if not known at context creation)."""
        self.record_id = record_id

    def set_error(
        self,
        message: str,
        error_code: str | None = None,
        error_type: str | None = None,
        error_category: str | None = None,
        error_details: dict | None = None,
    ):
        """Mark as error with optional structured error fields.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code (e.g., "ORDER_LIMIT_EXCEEDED")
            error_type: Exception class name (e.g., "ValidationError")
            error_category: Error category (e.g., "validation", "auth", "server")
            error_details: Structured error details (field errors, context, etc.)
        """
        self.outcome = "error"
        self.error_message = message
        if error_code is not None:
            self.error_code = error_code
        if error_type is not None:
            self.error_type = error_type
        if error_category is not None:
            self.error_category = error_category
        if error_details is not None:
            self.error_details = error_details

    def _extract_exception_context(self, exc_type, exc_val):
        """Extract structured error context from an exception.

        Args:
            exc_type: Exception type
            exc_val: Exception value/instance
        """
        self.outcome = "error"
        self.error_message = str(exc_val)
        self.error_type = exc_type.__name__

        # Extract error_code from exception attributes
        if hasattr(exc_val, "error_code"):
            self.error_code = str(exc_val.error_code)
        elif hasattr(exc_val, "code"):
            self.error_code = str(exc_val.code)

        # Extract error_details from exception attributes
        if hasattr(exc_val, "error_details"):
            self.error_details = exc_val.error_details
        elif hasattr(exc_val, "details"):
            self.error_details = exc_val.details

        # Infer error_category from exception type
        self.error_category = EXCEPTION_CATEGORY_MAP.get(self.error_type)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._extract_exception_context(exc_type, exc_val)

        await self._client.emit(
            entity=self.entity,
            action=self.action,
            record_id=self.record_id,
            from_state=self.from_state,
            to_state=self.to_state,
            outcome=self.outcome,
            error_message=self.error_message,
            error_code=self.error_code,
            error_type=self.error_type,
            error_category=self.error_category,
            error_details=self.error_details,
        )
