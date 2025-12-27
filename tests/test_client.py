"""Tests for INEV SDK client."""

import sys
from pathlib import Path

# Add parent directory to path to import inev_sdk
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from inev_sdk import INEVClient, InstrumentationContext


@pytest.mark.asyncio
async def test_client_emit():
    """Test basic event emission."""
    async with INEVClient(api_key="test_key", auto_batch=False) as client:
        with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
            event_id = await client.emit(
                entity="order",
                action="create",
                record_id="order_123",
                to_state="pending",
            )
            assert event_id
            mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_client_batching():
    """Test event batching."""
    client = INEVClient(api_key="test_key", batch_size=2)
    await client.start()

    with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
        await client.emit(entity="order", action="create")
        assert mock_send.call_count == 0  # Not flushed yet

        await client.emit(entity="order", action="update")
        assert mock_send.call_count == 1  # Batch size reached

    await client.close()


@pytest.mark.asyncio
async def test_instrumentation_context():
    """Test context manager for state transitions."""
    client = INEVClient(api_key="test_key", auto_batch=False)
    await client.start()

    with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
        async with InstrumentationContext(
            entity="order",
            record_id="123",
            from_state="pending",
            client=client,
        ) as ctx:
            ctx.set_to_state("shipped")

        mock_send.assert_called_once()
        events = mock_send.call_args[0][0]
        assert events[0]["entity"] == "order"
        assert events[0]["from_state"] == "pending"
        assert events[0]["to_state"] == "shipped"

    await client.close()


@pytest.mark.asyncio
async def test_context_error_handling():
    """Test that context manager captures errors."""
    client = INEVClient(api_key="test_key", auto_batch=False)
    await client.start()

    with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
        try:
            async with InstrumentationContext(
                entity="order",
                record_id="123",
                from_state="pending",
                client=client,
            ):
                raise ValueError("Test error")
        except ValueError:
            pass

        mock_send.assert_called_once()
        events = mock_send.call_args[0][0]
        assert events[0]["outcome"] == "error"
        assert "Test error" in events[0]["error_message"]

    await client.close()


@pytest.mark.asyncio
async def test_flush():
    """Test manual flush."""
    client = INEVClient(api_key="test_key", auto_batch=True, batch_size=100)
    await client.start()

    with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
        await client.emit(entity="order", action="create")
        assert mock_send.call_count == 0

        await client.flush()
        assert mock_send.call_count == 1

    await client.close()


@pytest.mark.asyncio
async def test_sync_emit():
    """Test synchronous emit mode."""
    client = INEVClient(api_key="test_key", sync_mode=True)

    with patch.object(client._sync_session, "post") as mock_post:
        event_id = client.emit_sync(entity="order", action="create", record_id="order_123")
        assert event_id
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_sync_emit_without_sync_mode():
    """Test that sync emit raises error when sync_mode=False."""
    client = INEVClient(api_key="test_key", sync_mode=False)

    with pytest.raises(RuntimeError, match="Sync mode not enabled"):
        client.emit_sync(entity="order", action="create")


@pytest.mark.asyncio
async def test_emit_with_custom_fields():
    """Test emitting events with custom fields."""
    async with INEVClient(api_key="test_key", auto_batch=False) as client:
        with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
            await client.emit(
                entity="order", action="create", record_id="order_123", custom_field="custom_value", another_field=42
            )

            events = mock_send.call_args[0][0]
            assert events[0]["custom_field"] == "custom_value"
            assert events[0]["another_field"] == 42


@pytest.mark.asyncio
async def test_background_flush():
    """Test background flush task."""
    client = INEVClient(
        api_key="test_key",
        auto_batch=True,
        batch_size=100,
        flush_interval=0.1,  # 100ms for testing
    )
    await client.start()

    with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
        await client.emit(entity="order", action="create")
        assert mock_send.call_count == 0

        # Wait for background flush
        await asyncio.sleep(0.15)
        assert mock_send.call_count == 1

    await client.close()


@pytest.mark.asyncio
async def test_close_flushes_pending():
    """Test that close() flushes pending events."""
    client = INEVClient(api_key="test_key", auto_batch=True, batch_size=100)
    await client.start()

    with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
        await client.emit(entity="order", action="create")
        assert mock_send.call_count == 0

        await client.close()
        assert mock_send.call_count == 1


@pytest.mark.asyncio
async def test_context_set_record_id():
    """Test setting record_id after context creation."""
    client = INEVClient(api_key="test_key", auto_batch=False)
    await client.start()

    with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
        async with InstrumentationContext(
            entity="order",
            from_state="pending",
            client=client,
        ) as ctx:
            # Record ID not known at context creation
            ctx.set_record_id("order_123")
            ctx.set_to_state("shipped")

        events = mock_send.call_args[0][0]
        assert events[0]["record_id"] == "order_123"

    await client.close()


@pytest.mark.asyncio
async def test_emit_all_fields():
    """Test emitting event with all possible fields."""
    async with INEVClient(api_key="test_key", auto_batch=False) as client:
        with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
            await client.emit(
                entity="order",
                action="ship",
                record_id="order_123",
                from_state="pending",
                to_state="shipped",
                outcome="success",
                error_message=None,
                user_id="user_456",
                session_id="session_789",
                parameters={"carrier": "UPS", "tracking": "1Z999"},
            )

            events = mock_send.call_args[0][0]
            event = events[0]
            assert event["entity"] == "order"
            assert event["action"] == "ship"
            assert event["record_id"] == "order_123"
            assert event["from_state"] == "pending"
            assert event["to_state"] == "shipped"
            assert event["outcome"] == "success"
            assert event["user_id"] == "user_456"
            assert event["session_id"] == "session_789"
            assert event["parameters"]["carrier"] == "UPS"
