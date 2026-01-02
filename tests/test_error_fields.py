"""Tests for structured error fields in SDK."""

from unittest.mock import AsyncMock, patch

import pytest

from inev_sdk import INEVClient, InstrumentationContext

# =============================================================================
# Step 8: Structured Error Fields Tests
# =============================================================================


class TestEmitStructuredErrorFields:
    """Test structured error fields in emit() method."""

    @pytest.mark.asyncio
    async def test_emit_with_error_code(self):
        """Test emitting event with error_code field."""
        async with INEVClient(api_key="test_key", auto_batch=False) as client:
            with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
                await client.emit(
                    entity="order",
                    action="create",
                    outcome="error",
                    error_code="ORDER_LIMIT_EXCEEDED",
                )

                events = mock_send.call_args[0][0]
                assert events[0]["error_code"] == "ORDER_LIMIT_EXCEEDED"

    @pytest.mark.asyncio
    async def test_emit_with_error_type(self):
        """Test emitting event with error_type field."""
        async with INEVClient(api_key="test_key", auto_batch=False) as client:
            with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
                await client.emit(
                    entity="order",
                    action="create",
                    outcome="error",
                    error_type="ValidationError",
                )

                events = mock_send.call_args[0][0]
                assert events[0]["error_type"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_emit_with_error_category(self):
        """Test emitting event with error_category field."""
        async with INEVClient(api_key="test_key", auto_batch=False) as client:
            with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
                await client.emit(
                    entity="order",
                    action="create",
                    outcome="error",
                    error_category="validation",
                )

                events = mock_send.call_args[0][0]
                assert events[0]["error_category"] == "validation"

    @pytest.mark.asyncio
    async def test_emit_with_error_details(self):
        """Test emitting event with error_details dict."""
        async with INEVClient(api_key="test_key", auto_batch=False) as client:
            with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
                error_details = {
                    "field_errors": {
                        "email": ["Invalid email format"],
                        "quantity": ["Must be greater than 0"],
                    },
                    "request_id": "req_123",
                }
                await client.emit(
                    entity="order",
                    action="create",
                    outcome="error",
                    error_details=error_details,
                )

                events = mock_send.call_args[0][0]
                assert events[0]["error_details"] == error_details
                assert events[0]["error_details"]["field_errors"]["email"] == ["Invalid email format"]

    @pytest.mark.asyncio
    async def test_emit_with_all_error_fields(self):
        """Test emitting event with all structured error fields."""
        async with INEVClient(api_key="test_key", auto_batch=False) as client:
            with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
                await client.emit(
                    entity="order",
                    action="create",
                    outcome="error",
                    error_message="Validation failed",
                    error_code="VALIDATION_ERROR",
                    error_type="ValidationError",
                    error_category="validation",
                    error_details={"field": "email", "reason": "invalid format"},
                )

                events = mock_send.call_args[0][0]
                assert events[0]["error_message"] == "Validation failed"
                assert events[0]["error_code"] == "VALIDATION_ERROR"
                assert events[0]["error_type"] == "ValidationError"
                assert events[0]["error_category"] == "validation"
                assert events[0]["error_details"] == {"field": "email", "reason": "invalid format"}

    @pytest.mark.asyncio
    async def test_emit_error_fields_default_to_none(self):
        """Test that error fields default to None when not provided."""
        async with INEVClient(api_key="test_key", auto_batch=False) as client:
            with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
                await client.emit(
                    entity="order",
                    action="create",
                    outcome="success",
                )

                events = mock_send.call_args[0][0]
                assert events[0]["error_code"] is None
                assert events[0]["error_type"] is None
                assert events[0]["error_category"] is None
                assert events[0]["error_details"] is None

    @pytest.mark.asyncio
    async def test_emit_backward_compatible(self):
        """Test that existing code without new error fields still works."""
        async with INEVClient(api_key="test_key", auto_batch=False) as client:
            with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
                # Old-style call should still work
                await client.emit(
                    entity="order",
                    action="create",
                    record_id="order_123",
                    outcome="error",
                    error_message="Something went wrong",
                )

                events = mock_send.call_args[0][0]
                assert events[0]["entity"] == "order"
                assert events[0]["action"] == "create"
                assert events[0]["error_message"] == "Something went wrong"


class TestEmitSyncStructuredErrorFields:
    """Test structured error fields in emit_sync() method."""

    def test_emit_sync_with_all_error_fields(self):
        """Test sync emit with all structured error fields."""
        client = INEVClient(api_key="test_key", sync_mode=True)

        with patch.object(client._sync_session, "post") as mock_post:
            client.emit_sync(
                entity="order",
                action="create",
                outcome="error",
                error_message="Validation failed",
                error_code="VALIDATION_ERROR",
                error_type="ValidationError",
                error_category="validation",
                error_details={"field": "email"},
            )

            call_args = mock_post.call_args
            events = call_args[1]["json"]["events"]
            assert events[0]["error_code"] == "VALIDATION_ERROR"
            assert events[0]["error_type"] == "ValidationError"
            assert events[0]["error_category"] == "validation"
            assert events[0]["error_details"] == {"field": "email"}


class TestTrackStructuredErrorFields:
    """Test structured error fields in track() method."""

    @pytest.mark.asyncio
    async def test_track_with_all_error_fields(self):
        """Test track method with all structured error fields."""
        async with INEVClient(api_key="test_key", auto_batch=False) as client:
            with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
                await client.track(
                    action="create_order",
                    outcome="error",
                    error_message="Order limit exceeded",
                    error_code="ORDER_LIMIT",
                    error_type="BusinessRuleError",
                    error_category="business_rule",
                    error_details={"limit": 100, "current": 105},
                )

                events = mock_send.call_args[0][0]
                assert events[0]["error_code"] == "ORDER_LIMIT"
                assert events[0]["error_type"] == "BusinessRuleError"
                assert events[0]["error_category"] == "business_rule"
                assert events[0]["error_details"] == {"limit": 100, "current": 105}


# =============================================================================
# Step 9: emit_error() Helper Method Tests
# =============================================================================


class TestEmitErrorHelper:
    """Test emit_error() helper method for automatic exception context extraction."""

    @pytest.mark.asyncio
    async def test_emit_error_extracts_exception_type(self):
        """Test that emit_error extracts exception class name."""
        async with INEVClient(api_key="test_key", auto_batch=False) as client:
            with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
                try:
                    raise ValueError("Invalid input")
                except ValueError as e:
                    await client.emit_error(
                        entity="order",
                        action="create",
                        exception=e,
                    )

                events = mock_send.call_args[0][0]
                assert events[0]["error_type"] == "ValueError"
                assert events[0]["error_message"] == "Invalid input"
                assert events[0]["outcome"] == "error"

    @pytest.mark.asyncio
    async def test_emit_error_extracts_error_code_attribute(self):
        """Test that emit_error extracts error_code from exception attribute."""

        class CustomError(Exception):
            def __init__(self, message, code):
                super().__init__(message)
                self.error_code = code

        async with INEVClient(api_key="test_key", auto_batch=False) as client:
            with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
                try:
                    raise CustomError("Order not found", "ORDER_NOT_FOUND")
                except CustomError as e:
                    await client.emit_error(
                        entity="order",
                        action="get",
                        exception=e,
                    )

                events = mock_send.call_args[0][0]
                assert events[0]["error_code"] == "ORDER_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_emit_error_extracts_code_attribute(self):
        """Test that emit_error extracts 'code' attribute as error_code."""

        class HTTPError(Exception):
            def __init__(self, message, code):
                super().__init__(message)
                self.code = code

        async with INEVClient(api_key="test_key", auto_batch=False) as client:
            with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
                try:
                    raise HTTPError("Not found", 404)
                except HTTPError as e:
                    await client.emit_error(
                        entity="order",
                        action="get",
                        exception=e,
                    )

                events = mock_send.call_args[0][0]
                assert events[0]["error_code"] == "404"

    @pytest.mark.asyncio
    async def test_emit_error_extracts_details_attribute(self):
        """Test that emit_error extracts details from exception attribute."""

        class ValidationError(Exception):
            def __init__(self, message, details):
                super().__init__(message)
                self.details = details

        async with INEVClient(api_key="test_key", auto_batch=False) as client:
            with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
                try:
                    raise ValidationError("Invalid fields", {"email": "Invalid format"})
                except ValidationError as e:
                    await client.emit_error(
                        entity="order",
                        action="create",
                        exception=e,
                    )

                events = mock_send.call_args[0][0]
                assert events[0]["error_details"] == {"email": "Invalid format"}

    @pytest.mark.asyncio
    async def test_emit_error_extracts_error_details_attribute(self):
        """Test that emit_error extracts error_details attribute."""

        class DetailedError(Exception):
            def __init__(self, message, error_details):
                super().__init__(message)
                self.error_details = error_details

        async with INEVClient(api_key="test_key", auto_batch=False) as client:
            with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
                try:
                    raise DetailedError("Failed", {"request_id": "req_123"})
                except DetailedError as e:
                    await client.emit_error(
                        entity="order",
                        action="create",
                        exception=e,
                    )

                events = mock_send.call_args[0][0]
                assert events[0]["error_details"] == {"request_id": "req_123"}

    @pytest.mark.asyncio
    async def test_emit_error_with_traceback(self):
        """Test emit_error includes traceback when requested."""
        async with INEVClient(api_key="test_key", auto_batch=False) as client:
            with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
                try:
                    raise ValueError("Test error")
                except ValueError as e:
                    await client.emit_error(
                        entity="order",
                        action="create",
                        exception=e,
                        include_traceback=True,
                    )

                events = mock_send.call_args[0][0]
                assert "traceback" in events[0]["error_details"]
                assert "ValueError" in events[0]["error_details"]["traceback"]

    @pytest.mark.asyncio
    async def test_emit_error_without_traceback_by_default(self):
        """Test emit_error does not include traceback by default."""
        async with INEVClient(api_key="test_key", auto_batch=False) as client:
            with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
                try:
                    raise ValueError("Test error")
                except ValueError as e:
                    await client.emit_error(
                        entity="order",
                        action="create",
                        exception=e,
                    )

                events = mock_send.call_args[0][0]
                # error_details should be None or not contain traceback
                error_details = events[0].get("error_details")
                if error_details:
                    assert "traceback" not in error_details

    @pytest.mark.asyncio
    async def test_emit_error_with_additional_kwargs(self):
        """Test emit_error passes through additional kwargs."""
        async with INEVClient(api_key="test_key", auto_batch=False) as client:
            with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
                try:
                    raise ValueError("Test error")
                except ValueError as e:
                    await client.emit_error(
                        entity="order",
                        action="create",
                        exception=e,
                        user_id="user_123",
                        record_id="order_456",
                    )

                events = mock_send.call_args[0][0]
                assert events[0]["user_id"] == "user_123"
                assert events[0]["record_id"] == "order_456"

    @pytest.mark.asyncio
    async def test_emit_error_infers_category_from_exception(self):
        """Test emit_error infers error_category from exception type."""
        async with INEVClient(api_key="test_key", auto_batch=False) as client:
            with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
                # ValueError -> validation category
                try:
                    raise ValueError("Invalid input")
                except ValueError as e:
                    await client.emit_error(
                        entity="order",
                        action="create",
                        exception=e,
                    )

                events = mock_send.call_args[0][0]
                assert events[0]["error_category"] == "validation"

    @pytest.mark.asyncio
    async def test_emit_error_infers_category_permission(self):
        """Test emit_error infers auth category from PermissionError."""
        async with INEVClient(api_key="test_key", auto_batch=False) as client:
            with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
                try:
                    raise PermissionError("Access denied")
                except PermissionError as e:
                    await client.emit_error(
                        entity="order",
                        action="create",
                        exception=e,
                    )

                events = mock_send.call_args[0][0]
                assert events[0]["error_category"] == "auth"

    @pytest.mark.asyncio
    async def test_emit_error_returns_event_id(self):
        """Test emit_error returns event ID."""
        async with INEVClient(api_key="test_key", auto_batch=False) as client:
            with patch.object(client, "_send", new_callable=AsyncMock):
                try:
                    raise ValueError("Test")
                except ValueError as e:
                    event_id = await client.emit_error(
                        entity="order",
                        action="create",
                        exception=e,
                    )

                assert event_id is not None
                assert isinstance(event_id, str)


# =============================================================================
# Step 10: Enhanced Context Manager Tests
# =============================================================================


class TestInstrumentationContextErrorFields:
    """Test enhanced error capture in InstrumentationContext."""

    @pytest.mark.asyncio
    async def test_context_captures_error_type(self):
        """Test context manager captures exception class name."""
        client = INEVClient(api_key="test_key", auto_batch=False)
        await client.start()

        with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
            try:
                async with InstrumentationContext(
                    entity="order",
                    record_id="123",
                    client=client,
                ):
                    raise ValueError("Invalid value")
            except ValueError:
                pass

            events = mock_send.call_args[0][0]
            assert events[0]["error_type"] == "ValueError"
            assert events[0]["outcome"] == "error"

        await client.close()

    @pytest.mark.asyncio
    async def test_context_captures_error_code_from_exception(self):
        """Test context manager captures error_code from exception attribute."""

        class BusinessError(Exception):
            def __init__(self, message, error_code):
                super().__init__(message)
                self.error_code = error_code

        client = INEVClient(api_key="test_key", auto_batch=False)
        await client.start()

        with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
            try:
                async with InstrumentationContext(
                    entity="order",
                    record_id="123",
                    client=client,
                ):
                    raise BusinessError("Limit exceeded", "ORDER_LIMIT")
            except BusinessError:
                pass

            events = mock_send.call_args[0][0]
            assert events[0]["error_code"] == "ORDER_LIMIT"

        await client.close()

    @pytest.mark.asyncio
    async def test_context_captures_error_details_from_exception(self):
        """Test context manager captures error_details from exception attribute."""

        class DetailedError(Exception):
            def __init__(self, message, details):
                super().__init__(message)
                self.details = details

        client = INEVClient(api_key="test_key", auto_batch=False)
        await client.start()

        with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
            try:
                async with InstrumentationContext(
                    entity="order",
                    record_id="123",
                    client=client,
                ):
                    raise DetailedError("Failed", {"field": "quantity"})
            except DetailedError:
                pass

            events = mock_send.call_args[0][0]
            assert events[0]["error_details"] == {"field": "quantity"}

        await client.close()

    @pytest.mark.asyncio
    async def test_context_no_error_fields_on_success(self):
        """Test context manager doesn't set error fields on success."""
        client = INEVClient(api_key="test_key", auto_batch=False)
        await client.start()

        with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
            async with InstrumentationContext(
                entity="order",
                record_id="123",
                client=client,
            ) as ctx:
                ctx.set_to_state("completed")

            events = mock_send.call_args[0][0]
            assert events[0]["outcome"] == "success"
            assert events[0].get("error_type") is None
            assert events[0].get("error_code") is None
            assert events[0].get("error_details") is None

        await client.close()

    @pytest.mark.asyncio
    async def test_context_manual_error_fields(self):
        """Test context manager allows manual error field setting."""
        client = INEVClient(api_key="test_key", auto_batch=False)
        await client.start()

        with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
            async with InstrumentationContext(
                entity="order",
                record_id="123",
                client=client,
            ) as ctx:
                ctx.set_error("Manual error", error_code="MANUAL_ERROR")

            events = mock_send.call_args[0][0]
            assert events[0]["outcome"] == "error"
            assert events[0]["error_message"] == "Manual error"
            assert events[0]["error_code"] == "MANUAL_ERROR"

        await client.close()

    @pytest.mark.asyncio
    async def test_context_set_error_with_details(self):
        """Test context manager set_error() with details."""
        client = INEVClient(api_key="test_key", auto_batch=False)
        await client.start()

        with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
            async with InstrumentationContext(
                entity="order",
                record_id="123",
                client=client,
            ) as ctx:
                ctx.set_error(
                    "Validation failed",
                    error_code="VALIDATION_ERROR",
                    error_type="ValidationError",
                    error_category="validation",
                    error_details={"field": "email"},
                )

            events = mock_send.call_args[0][0]
            assert events[0]["error_message"] == "Validation failed"
            assert events[0]["error_code"] == "VALIDATION_ERROR"
            assert events[0]["error_type"] == "ValidationError"
            assert events[0]["error_category"] == "validation"
            assert events[0]["error_details"] == {"field": "email"}

        await client.close()
