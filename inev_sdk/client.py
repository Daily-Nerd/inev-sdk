"""INEV SDK Client for domain event capture."""

import asyncio
import traceback
import uuid
from datetime import datetime, timezone

import httpx

# SDK identifier sent with all events
SDK_SOURCE = "inev-python-sdk"

# Mapping of exception types to error categories
EXCEPTION_CATEGORY_MAP = {
    # Validation errors
    "ValueError": "validation",
    "TypeError": "validation",
    "ValidationError": "validation",
    "InvalidArgumentError": "validation",
    # Authentication/Authorization errors
    "PermissionError": "auth",
    "AuthenticationError": "auth",
    "AuthorizationError": "auth",
    "UnauthorizedError": "auth",
    "ForbiddenError": "auth",
    # Resource errors
    "FileNotFoundError": "not_found",
    "NotFoundError": "not_found",
    "DoesNotExist": "not_found",
    "ObjectDoesNotExist": "not_found",
    # Connection/Network errors
    "ConnectionError": "network",
    "TimeoutError": "network",
    "NetworkError": "network",
    # Rate limiting
    "RateLimitError": "rate_limit",
    "TooManyRequestsError": "rate_limit",
    # Server errors
    "RuntimeError": "server",
    "InternalError": "server",
}


class INEVClient:
    """INEV SDK for domain event capture.

    Features:
    - Async-first design with httpx
    - Automatic batching with configurable size and interval
    - Background flush task for time-based flushing
    - Graceful shutdown with pending event flush
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.inev.io",
        environment: str = "production",
        auto_batch: bool = True,
        batch_size: int = 100,
        flush_interval: float = 5.0,
        sync_mode: bool = False,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.environment = environment
        self._session: httpx.AsyncClient | None = None
        self._sync_session: httpx.Client | None = None if not sync_mode else httpx.Client()
        self._batch: list[dict] = []
        self._auto_batch = auto_batch
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._flush_task: asyncio.Task | None = None
        self._running = False
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self):
        """Start the client and background flush task."""
        if self._running:
            return
        self._running = True
        self._session = httpx.AsyncClient()
        if self._auto_batch and self._flush_interval > 0:
            self._flush_task = asyncio.create_task(self._background_flush())

    async def _background_flush(self):
        """Background task that flushes events at regular intervals."""
        while self._running:
            try:
                await asyncio.sleep(self._flush_interval)
                if self._batch:
                    await self.flush()
            except asyncio.CancelledError:
                break
            except Exception:
                pass  # Log but don't crash

    async def emit(
        self,
        entity: str,
        action: str,
        record_id: str | None = None,
        from_state: str | None = None,
        to_state: str | None = None,
        outcome: str = "success",
        error_message: str | None = None,
        error_code: str | None = None,
        error_type: str | None = None,
        error_category: str | None = None,
        error_details: dict | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        parameters: dict | None = None,
        source: str | None = None,
        **kwargs,
    ) -> str:
        """Emit a domain event (async).

        Args:
            entity: Entity name (e.g., "order", "user")
            action: Action name (e.g., "create", "update")
            record_id: Optional record identifier
            from_state: Optional source state
            to_state: Optional target state
            outcome: Event outcome - "success", "error", or "partial"
            error_message: Human-readable error message
            error_code: Machine-readable error code (e.g., "ORDER_LIMIT_EXCEEDED")
            error_type: Exception class name (e.g., "ValidationError")
            error_category: Error category (e.g., "validation", "auth", "server")
            error_details: Structured error details (field errors, context, etc.)
            user_id: Optional user identifier
            session_id: Optional session identifier
            parameters: Optional event parameters
            source: Optional source identifier
            **kwargs: Additional fields passed through to API

        Returns:
            Event ID (UUID string)
        """
        event_id = str(uuid.uuid4())
        event = {
            "event_id": event_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "entity": entity,
            "action": action,
            "record_id": record_id,
            "from_state": from_state,
            "to_state": to_state,
            "outcome": outcome,
            "error_message": error_message,
            "error_code": error_code,
            "error_type": error_type,
            "error_category": error_category,
            "error_details": error_details,
            "user_id": user_id,
            "session_id": session_id,
            "parameters": parameters or {},
            "environment": self.environment,
            "source": source or SDK_SOURCE,  # Default to SDK identifier
            **kwargs,
        }

        if self._auto_batch:
            async with self._lock:
                self._batch.append(event)
                if len(self._batch) >= self._batch_size:
                    await self._flush_locked()
        else:
            await self._send([event])

        return event_id

    async def track(
        self,
        action: str,
        outcome: str = "success",
        *,
        user_id: str | None = None,
        session_id: str | None = None,
        error_message: str | None = None,
        error_code: str | None = None,
        error_type: str | None = None,
        error_category: str | None = None,
        error_details: dict | None = None,
        parameters: dict | None = None,
        entity: str | None = None,
        from_state: str | None = None,
        to_state: str | None = None,
        record_id: str | None = None,
        timestamp: datetime | None = None,
        source: str | None = None,
        **kwargs,
    ) -> str:
        """Track an auto-instrumented event (entity optional, enriched server-side).

        This method is designed for auto-instrumentation use cases where entity/record_id
        may not be known at capture time and will be enriched by the server.

        For manual domain events where entity is known, use emit() instead.

        Args:
            action: Action name (e.g., "create_project", "delete_user")
            outcome: Event outcome - "success", "error", or "partial"
            user_id: Optional user identifier
            session_id: Optional session identifier
            error_message: Error message if outcome is "error"
            error_code: Machine-readable error code (e.g., "ORDER_LIMIT_EXCEEDED")
            error_type: Exception class name (e.g., "ValidationError")
            error_category: Error category (e.g., "validation", "auth", "server")
            error_details: Structured error details (field errors, context, etc.)
            parameters: Optional event parameters (captures request/response data)
            entity: Optional entity name (if None, enriched server-side)
            from_state: Optional source state
            to_state: Optional target state
            record_id: Optional record identifier (if None, enriched server-side)
            timestamp: Optional timestamp (defaults to now)
            **kwargs: Additional fields passed through to API

        Returns:
            Event ID (UUID string)
        """
        event_id = str(uuid.uuid4())
        event_timestamp = timestamp or datetime.now(timezone.utc)

        event = {
            "event_id": event_id,
            "timestamp": event_timestamp.isoformat(),
            "action": action,
            "outcome": outcome,
            "error_message": error_message,
            "error_code": error_code,
            "error_type": error_type,
            "error_category": error_category,
            "error_details": error_details,
            "user_id": user_id,
            "session_id": session_id,
            "parameters": parameters or {},
            "environment": self.environment,
            "source": source or SDK_SOURCE,  # Default to SDK identifier
            **kwargs,
        }

        # Add optional fields only if provided (server will enrich if missing)
        if entity is not None:
            event["entity"] = entity
        if record_id is not None:
            event["record_id"] = record_id
        if from_state is not None:
            event["from_state"] = from_state
        if to_state is not None:
            event["to_state"] = to_state

        if self._auto_batch:
            async with self._lock:
                self._batch.append(event)
                if len(self._batch) >= self._batch_size:
                    await self._flush_locked()
        else:
            await self._send([event])

        return event_id

    def emit_sync(
        self,
        entity: str,
        action: str,
        record_id: str | None = None,
        from_state: str | None = None,
        to_state: str | None = None,
        outcome: str = "success",
        error_message: str | None = None,
        error_code: str | None = None,
        error_type: str | None = None,
        error_category: str | None = None,
        error_details: dict | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        parameters: dict | None = None,
        source: str | None = None,
        **kwargs,
    ) -> str:
        """Emit a domain event (sync - for serverless environments).

        Args:
            entity: Entity name (e.g., "order", "user")
            action: Action name (e.g., "create", "update")
            record_id: Optional record identifier
            from_state: Optional source state
            to_state: Optional target state
            outcome: Event outcome - "success", "error", or "partial"
            error_message: Human-readable error message
            error_code: Machine-readable error code (e.g., "ORDER_LIMIT_EXCEEDED")
            error_type: Exception class name (e.g., "ValidationError")
            error_category: Error category (e.g., "validation", "auth", "server")
            error_details: Structured error details (field errors, context, etc.)
            user_id: Optional user identifier
            session_id: Optional session identifier
            parameters: Optional event parameters
            source: Optional source identifier
            **kwargs: Additional fields passed through to API

        Returns:
            Event ID (UUID string)
        """
        if not self._sync_session:
            raise RuntimeError("Sync mode not enabled. Initialize with sync_mode=True")

        event_id = str(uuid.uuid4())
        event = {
            "event_id": event_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "entity": entity,
            "action": action,
            "record_id": record_id,
            "from_state": from_state,
            "to_state": to_state,
            "outcome": outcome,
            "error_message": error_message,
            "error_code": error_code,
            "error_type": error_type,
            "error_category": error_category,
            "error_details": error_details,
            "user_id": user_id,
            "session_id": session_id,
            "parameters": parameters or {},
            "environment": self.environment,
            "source": source or SDK_SOURCE,  # Default to SDK identifier
            **kwargs,
        }

        self._sync_session.post(
            f"{self.base_url}/api/v1/events/", json={"events": [event]}, headers={"X-API-Key": self.api_key}
        )

        return event_id

    async def emit_error(
        self,
        entity: str,
        action: str,
        exception: Exception,
        include_traceback: bool = False,
        **kwargs,
    ) -> str:
        """Emit error event with automatic exception context extraction.

        This helper method automatically extracts error context from an exception:
        - error_type: Exception class name
        - error_message: Exception message
        - error_code: From exception.error_code or exception.code attribute
        - error_details: From exception.details or exception.error_details attribute
        - error_category: Inferred from exception type

        Args:
            entity: Entity name (e.g., "order", "user")
            action: Action name (e.g., "create", "update")
            exception: The exception to extract context from
            include_traceback: Whether to include traceback in error_details
            **kwargs: Additional fields passed to emit()

        Returns:
            Event ID (UUID string)
        """
        error_type = type(exception).__name__
        error_message = str(exception)

        # Extract error_code from exception attributes
        error_code = None
        if hasattr(exception, "error_code"):
            error_code = str(exception.error_code)
        elif hasattr(exception, "code"):
            error_code = str(exception.code)

        # Extract error_details from exception attributes
        error_details = None
        if hasattr(exception, "error_details"):
            error_details = exception.error_details
        elif hasattr(exception, "details"):
            error_details = exception.details

        # Infer error_category from exception type
        error_category = EXCEPTION_CATEGORY_MAP.get(error_type)

        # Include traceback if requested
        if include_traceback:
            tb_str = traceback.format_exception(type(exception), exception, exception.__traceback__)
            if error_details is None:
                error_details = {}
            if isinstance(error_details, dict):
                error_details = dict(error_details)  # Create a copy
                error_details["traceback"] = "".join(tb_str)

        return await self.emit(
            entity=entity,
            action=action,
            outcome="error",
            error_message=error_message,
            error_code=error_code,
            error_type=error_type,
            error_category=error_category,
            error_details=error_details,
            **kwargs,
        )

    async def flush(self):
        """Send batched events."""
        async with self._lock:
            await self._flush_locked()

    async def _flush_locked(self):
        """Flush while already holding the lock."""
        if self._batch:
            batch = self._batch
            self._batch = []
            await self._send(batch)

    async def _send(self, events: list[dict]):
        """Send events to INEV API."""
        if not self._session:
            self._session = httpx.AsyncClient()
        await self._session.post(
            f"{self.base_url}/api/v1/events/", json={"events": events}, headers={"X-API-Key": self.api_key}
        )

    async def close(self):
        """Stop background flush, flush pending events, close client."""
        self._running = False

        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        await self.flush()

        if self._session:
            await self._session.aclose()
        if self._sync_session:
            self._sync_session.close()
