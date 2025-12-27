"""
FastAPI/Starlette middleware for auto-instrumentation.

This middleware automatically captures all HTTP requests/responses as domain events
and sends them to INEV for ILA analysis. It mirrors the backend's IntentMonitorMiddleware
pattern but is designed for customer applications.

Features:
- Zero-code integration (just add middleware)
- Non-blocking event queuing (never slows requests)
- Configurable path exclusions (health checks, docs)
- Smart action extraction from HTTP method + path
- Auto-detection of success/error outcomes
- Optional server-side enrichment via EventMappingConfig
"""

import asyncio
import json
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..client import INEVClient
from ..utils.action_naming import generate_action_name


class INEVMiddleware(BaseHTTPMiddleware):
    """
    Auto-capture all API interactions as domain events.

    This middleware transparently captures every API request/response and sends
    it to INEV for ILA analysis. It's designed to be zero-friction:
    - No code changes needed in route handlers
    - Non-blocking (events are batched and sent asynchronously)
    - Configurable exclusions for health checks, etc.
    - Smart action extraction from paths

    Usage:
        from fastapi import FastAPI
        from inev_sdk.integrations.fastapi import INEVMiddleware

        app = FastAPI()
        app.add_middleware(
            INEVMiddleware,
            api_key="sk_live_...",
            project_id="proj_123",
            excluded_paths=["/health", "/docs"],
        )

    The middleware captures raw HTTP events and relies on server-side EventMappingConfig
    for entity/state enrichment (Hybrid Event Capture Tier 1).
    """

    # Default paths to skip monitoring
    DEFAULT_EXCLUDE_PATHS = [
        "/health",
        "/ready",
        "/metrics",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/favicon.ico",
    ]

    # HTTP status code to error message mapping
    STATUS_MESSAGES = {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        422: "Validation Error",
        429: "Rate Limited",
        500: "Internal Server Error",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout",
    }

    def __init__(
        self,
        app,
        api_key: str,
        project_id: str,
        endpoint: str = "https://api.inev.io",
        excluded_paths: list[str] | None = None,
        action_extractor: Callable[[Request], str] | None = None,
        auto_enrich: bool = True,
        batch_size: int = 100,
        flush_interval: float = 5.0,
        environment: str = "production",
    ):
        """
        Initialize the INEV auto-instrumentation middleware.

        Args:
            app: The FastAPI application
            api_key: INEV API key for authentication
            project_id: Project to associate events with
            endpoint: API endpoint (default: production)
            excluded_paths: List of path prefixes to skip monitoring (defaults to health checks, docs)
            action_extractor: Custom function to extract action name from request (optional)
            auto_enrich: Whether to use server-side enrichment (default True)
            batch_size: Number of events to batch before sending (default 100)
            flush_interval: Time interval in seconds to flush events (default 5.0)
            environment: Environment tag for events (default "production")
        """
        super().__init__(app)
        self.project_id = project_id
        self.exclude_paths = excluded_paths if excluded_paths is not None else self.DEFAULT_EXCLUDE_PATHS
        self.action_extractor = action_extractor or self._default_action_extractor
        self.auto_enrich = auto_enrich
        self.environment = environment

        # Initialize INEV client with batching
        self._client = INEVClient(
            api_key=api_key,
            base_url=endpoint,
            environment=environment,
            auto_batch=True,
            batch_size=batch_size,
            flush_interval=flush_interval,
        )

        # Start the client's background flush task
        self._startup_task: asyncio.Task | None = None

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process the request and capture it as a domain event.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response: HTTP response (unchanged)
        """
        # Skip excluded paths (health checks, docs, etc.)
        if self._should_skip(request.url.path):
            return await call_next(request)

        # Ensure client is started
        if not self._client._running:
            await self._client.start()

        # Capture request start time for duration calculation
        start_time = datetime.now(timezone.utc)

        # Extract request context (before processing)
        action = self.action_extractor(request)
        user_id = self._extract_user_id(request)
        session_id = request.headers.get("x-session-id")
        source = self._extract_source(request)

        # Process the request and capture outcome
        response = None
        error_message = None
        outcome = "success"

        try:
            # Call the next handler in the chain
            response = await call_next(request)

            # Determine outcome from status code
            if response.status_code >= 400:
                outcome = "error"
                # Extract detailed error message from response body
                error_message = await self._extract_error_message(response)

            return response

        except Exception as e:
            # Request failed with exception
            outcome = "error"
            error_message = f"{type(e).__name__}: {str(e)}"
            raise

        finally:
            # Queue the event (always runs, even if exception)
            await self._queue_event(
                start_time=start_time,
                action=action,
                outcome=outcome,
                user_id=user_id,
                session_id=session_id,
                error_message=error_message,
                request=request,
                response=response,
                source=source,
            )

    async def _queue_event(
        self,
        start_time: datetime,
        action: str,
        outcome: str,
        user_id: str | None,
        session_id: str | None,
        error_message: str | None,
        request: Request,
        response: Response | None,
        source: str | None = None,
    ):
        """
        Create domain event and queue it via the INEV client.

        Args:
            start_time: Request start timestamp
            action: Extracted action name
            outcome: "success" or "error"
            user_id: User identifier (if available)
            session_id: Session identifier (if available)
            error_message: Error description (if error)
            request: Original HTTP request
            response: HTTP response (may be None if exception)
            source: Source type identifier (e.g., "api-client")
        """
        # Calculate request duration
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        # Build parameters dict with HTTP context
        parameters = {
            "path": str(request.url.path),
            "method": request.method,
            "status_code": response.status_code if response else 500,
            "duration_ms": round(duration_ms, 2),
            "query_params": dict(request.query_params),
        }

        # Build context dict
        context = {
            "project_id": self.project_id,
            "auto_enrich": self.auto_enrich,
        }
        if source:
            context["source"] = source

        # Emit event via INEV client (non-blocking batched send)
        try:
            await self._client.emit(
                entity=None,  # Server-side enrichment will infer this
                action=action,
                record_id=None,  # Server-side enrichment will infer this
                from_state=None,  # Server-side enrichment will infer this
                to_state=None,  # Server-side enrichment will infer this
                outcome=outcome,
                error_message=error_message,
                user_id=user_id,
                session_id=session_id,
                parameters=parameters,
                **context,
            )
        except Exception:
            # Never let event emission break the request
            # The client handles its own error logging
            pass

    def _should_skip(self, path: str) -> bool:
        """
        Check if path should be excluded from monitoring.

        Args:
            path: Request path to check

        Returns:
            bool: True if path should be skipped
        """
        return any(path.startswith(excluded) for excluded in self.exclude_paths)

    def _default_action_extractor(self, request: Request) -> str:
        """
        Extract semantic action name from request path and method.

        Generates semantic action names that include the full resource path:
        - POST /api/workspaces/{id}/members -> "post_workspace_members"
        - DELETE /api/projects/{id}/members/{member_id} -> "delete_project_member"
        - GET /api/workspaces/{id}/projects -> "get_workspace_projects"
        - PATCH /api/orders/{id}/status -> "patch_order_status"
        - GET /api/v1/orders -> "get_orders"

        Uses intelligent path parsing to:
        - Filter out UUID/ID segments
        - Singularize resource names where appropriate
        - Preserve nested resource context

        Args:
            request: HTTP request

        Returns:
            str: Semantic action name (e.g., "post_workspace_members")
        """
        return generate_action_name(request.method, request.url.path)

    def _extract_user_id(self, request: Request) -> str | None:
        """
        Extract user ID from auth context.

        Tries multiple sources:
        1. request.state.user_id (set by auth middleware)
        2. X-API-Key header (masked)
        3. Authorization header prefix (masked)
        4. X-User-ID header

        Args:
            request: HTTP request

        Returns:
            str | None: User identifier or None if not authenticated
        """
        # Check if auth middleware set user_id in request state
        if hasattr(request.state, "user_id"):
            return request.state.user_id

        # Check X-User-ID header (explicit user tracking)
        user_id = request.headers.get("x-user-id")
        if user_id:
            return user_id

        # Check X-API-Key header
        api_key = request.headers.get("x-api-key", "")
        if api_key and len(api_key) > 12:
            # Return masked version for tracking (don't expose full token)
            return f"apikey_{api_key[8:16]}..."

        # Fall back to extracting from Authorization header
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Strip "Bearer " prefix
            if len(token) > 8:
                return f"bearer_{token[:8]}..."
            return None

        # Check for session cookie
        session_cookie = request.cookies.get("session", "")
        if session_cookie and len(session_cookie) > 8:
            return f"session_{session_cookie[:8]}..."

        return None

    def _extract_source(self, request: Request) -> str:
        """
        Identify the source of the request.

        Returns:
            str: Source identifier (e.g., "frontend", "mobile", "api-client")
        """
        # Check X-Client-Type header (explicit client type)
        client_type = request.headers.get("x-client-type", "").lower()
        if client_type:
            return client_type

        # Check User-Agent for common patterns
        user_agent = request.headers.get("user-agent", "").lower()
        if "mobile" in user_agent or "android" in user_agent or "iphone" in user_agent:
            return "mobile"
        elif "mozilla" in user_agent or "chrome" in user_agent or "safari" in user_agent:
            return "browser"
        elif "python" in user_agent or "httpx" in user_agent or "requests" in user_agent:
            return "api-client"

        return "unknown"

    def _get_error_message(self, status_code: int) -> str:
        """
        Get human-readable error message for HTTP status code.

        Args:
            status_code: HTTP status code

        Returns:
            str: Error message description
        """
        return self.STATUS_MESSAGES.get(status_code, f"HTTP {status_code}")

    def _format_validation_error(self, detail: list[dict[str, Any]]) -> str:
        """
        Format FastAPI validation error detail into human-readable message.

        Args:
            detail: List of validation error dicts with 'loc', 'msg', 'type' keys

        Returns:
            str: Formatted error message like "Validation Error: body.email - field required"
        """
        if not detail:
            return "Validation Error"

        error_parts = []
        for error in detail:
            loc = error.get("loc", [])
            msg = error.get("msg", "invalid")
            # Join location parts (e.g., ['body', 'email'] -> 'body.email')
            loc_str = ".".join(str(part) for part in loc if part)
            error_parts.append(f"{loc_str} - {msg}" if loc_str else msg)

        return f"Validation Error: {'; '.join(error_parts)}"

    async def _extract_error_message(self, response: Response) -> str:
        """
        Extract detailed error message from response body.

        Handles:
        - FastAPI validation errors (422 with detail array)
        - Generic JSON errors (with detail or message field)
        - Non-JSON responses (uses status text)

        Args:
            response: HTTP response

        Returns:
            str: Human-readable error message
        """
        # Start with generic status message
        base_message = self._get_error_message(response.status_code)

        # Try to extract response body for 4xx/5xx errors
        if response.status_code < 400:
            return base_message

        try:
            # Get response body (we need to capture it before it's consumed)
            # For Starlette Response objects, we can access the body
            if hasattr(response, "body"):
                body = response.body
                if isinstance(body, bytes):
                    body_str = body.decode("utf-8")
                else:
                    body_str = str(body)

                # Try to parse as JSON
                try:
                    error_data = json.loads(body_str)

                    # Handle FastAPI validation errors (422)
                    if response.status_code == 422 and "detail" in error_data:
                        detail = error_data["detail"]
                        if isinstance(detail, list):
                            return self._format_validation_error(detail)
                        elif isinstance(detail, str):
                            return f"Validation Error: {detail}"

                    # Handle generic JSON errors with detail field
                    if "detail" in error_data:
                        detail = error_data["detail"]
                        if isinstance(detail, str):
                            return detail
                        elif isinstance(detail, dict):
                            # Try to extract message from detail object
                            msg = detail.get("message") or detail.get("msg") or str(detail)
                            return msg

                    # Handle errors with message field
                    if "message" in error_data:
                        return error_data["message"]

                    # Handle errors with error field
                    if "error" in error_data:
                        error = error_data["error"]
                        if isinstance(error, str):
                            return error
                        elif isinstance(error, dict) and "message" in error:
                            return error["message"]

                except json.JSONDecodeError:
                    # Not JSON, use body as-is if it's short enough
                    if len(body_str) < 200:
                        return f"{base_message}: {body_str}"

        except Exception:
            # If anything fails, fall back to generic message
            pass

        return base_message
