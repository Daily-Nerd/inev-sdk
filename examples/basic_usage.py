#!/usr/bin/env python3
"""Basic usage examples for INEV SDK."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for import
sys.path.insert(0, str(Path(__file__).parent.parent))

from inev_sdk import INEVClient, InstrumentationContext, configure, emit_domain_event


async def example_basic_emit():
    """Example 1: Basic event emission."""
    print("Example 1: Basic Event Emission")
    print("-" * 50)

    async with INEVClient(api_key="demo_key_12345", base_url="http://localhost:8000") as client:
        # Emit a simple domain event
        event_id = await client.emit(
            entity="order",
            action="create",
            record_id="order_123",
            to_state="pending",
            user_id="user_456",
            parameters={"total": 99.99, "items": 3},
        )
        print(f"✓ Event emitted with ID: {event_id}")


async def example_state_transition():
    """Example 2: State transition tracking."""
    print("\nExample 2: State Transition Tracking")
    print("-" * 50)

    async with INEVClient(api_key="demo_key_12345", base_url="http://localhost:8000") as client:
        # Track a complete state transition
        event_id = await client.emit(
            entity="payment",
            action="process",
            record_id="pay_789",
            from_state="pending",
            to_state="completed",
            user_id="user_456",
            parameters={"amount": 99.99, "method": "credit_card", "last4": "4242"},
        )
        print("✓ State transition tracked: pending → completed")
        print(f"✓ Event ID: {event_id}")


async def example_context_manager():
    """Example 3: Using context manager for automatic tracking."""
    print("\nExample 3: Context Manager for Automatic Tracking")
    print("-" * 50)

    async with INEVClient(api_key="demo_key_12345", base_url="http://localhost:8000") as client:
        # Use context manager to automatically track state changes
        async with InstrumentationContext(
            entity="shipment", record_id="ship_999", from_state="preparing", action="ship", client=client
        ) as ctx:
            # Simulate processing
            print("  Processing shipment...")
            await asyncio.sleep(0.1)

            # Set the target state
            ctx.set_to_state("shipped")
            print("✓ Shipment context tracked automatically")


async def example_error_handling():
    """Example 4: Automatic error capture."""
    print("\nExample 4: Automatic Error Capture")
    print("-" * 50)

    async with INEVClient(api_key="demo_key_12345", base_url="http://localhost:8000") as client:
        try:
            async with InstrumentationContext(
                entity="refund", record_id="refund_555", from_state="pending", action="process", client=client
            ):
                # Simulate an error
                print("  Processing refund...")
                raise ValueError("Insufficient funds for refund")
        except ValueError as e:
            print(f"✓ Error captured automatically: {e}")


async def example_batching():
    """Example 5: Automatic batching."""
    print("\nExample 5: Automatic Event Batching")
    print("-" * 50)

    async with INEVClient(
        api_key="demo_key_12345", base_url="http://localhost:8000", batch_size=5, flush_interval=1.0
    ) as client:
        # Emit multiple events - they'll be batched
        print("  Emitting 10 events...")
        for i in range(10):
            await client.emit(
                entity="notification", action="send", record_id=f"notif_{i}", parameters={"type": "email"}
            )

        print("✓ 10 events emitted with automatic batching")
        print("  (Events batched in groups of 5)")


async def example_decorator():
    """Example 6: Using decorators."""
    print("\nExample 6: Decorator Pattern")
    print("-" * 50)

    # Configure global client
    configure(api_key="demo_key_12345", base_url="http://localhost:8000")

    class Order:
        def __init__(self, id, status):
            self.id = id
            self.status = status

    @emit_domain_event(entity="order", action="create", record_id_attr="id", state_attr="status")
    async def create_order(order_id: str):
        """Business logic with automatic event emission."""
        await asyncio.sleep(0.1)  # Simulate DB operation
        return Order(id=order_id, status="pending")

    # Function will automatically emit event
    order = await create_order("order_888")
    print(f"✓ Order created: {order.id}")
    print("✓ Event automatically emitted via decorator")


async def example_custom_fields():
    """Example 7: Custom fields and metadata."""
    print("\nExample 7: Custom Fields and Metadata")
    print("-" * 50)

    async with INEVClient(api_key="demo_key_12345", base_url="http://localhost:8000") as client:
        await client.emit(
            entity="user",
            action="login",
            record_id="user_123",
            # Custom fields via kwargs
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0...",
            location="San Francisco, CA",
            ab_test_variant="new_checkout_v2",
            feature_flags=["dark_mode", "new_ui"],
        )
        print("✓ Event with custom metadata emitted")
        print("  Custom fields: ip_address, user_agent, location, ab_test_variant, feature_flags")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("INEV SDK - Python Usage Examples")
    print("=" * 60)

    try:
        await example_basic_emit()
        await example_state_transition()
        await example_context_manager()
        await example_error_handling()
        await example_batching()
        await example_decorator()
        await example_custom_fields()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Note: In production, these would send to actual INEV API
    # For demo purposes, these will fail to connect (expected)
    print("\nNote: Examples use mock API endpoint (http://localhost:8000)")
    print("In production, events would be sent to https://api.inev.io\n")

    asyncio.run(main())
