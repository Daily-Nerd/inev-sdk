# INEV SDK - Quick Start Guide

## Installation

```bash
pip install inev-sdk
```

## 30-Second Start

```python
from inev_sdk import INEVClient
import asyncio

async def main():
    async with INEVClient(api_key="your_api_key") as client:
        # Emit your first event
        event_id = await client.emit(
            entity="order",
            action="create",
            record_id="order_123",
            to_state="pending"
        )
        print(f"Event emitted: {event_id}")

asyncio.run(main())
```

## Common Patterns

### 1. Track State Transitions

```python
await client.emit(
    entity="payment",
    action="process",
    record_id="pay_456",
    from_state="pending",
    to_state="completed"
)
```

### 2. Automatic Error Tracking

```python
from inev_sdk import InstrumentationContext

async with InstrumentationContext(
    entity="refund",
    record_id="ref_789",
    from_state="pending",
    client=client
) as ctx:
    try:
        await process_refund()
        ctx.set_to_state("completed")
    except Exception as e:
        # Error automatically captured!
        raise
```

### 3. Decorator Pattern

```python
from inev_sdk import configure, emit_domain_event

# Configure once at startup
configure(api_key="your_api_key")

@emit_domain_event(
    entity="order",
    action="create",
    record_id_attr="id",
    state_attr="status"
)
async def create_order(data):
    order = Order(id=data["id"], status="pending")
    # Event automatically emitted!
    return order
```

### 4. Serverless (AWS Lambda)

```python
from inev_sdk import INEVClient

client = INEVClient(api_key="your_key", sync_mode=True)

def lambda_handler(event, context):
    # Use synchronous emit
    event_id = client.emit_sync(
        entity="order",
        action="process",
        record_id=event["order_id"]
    )
    return {"statusCode": 200}
```

### 5. High-Volume (Batching)

```python
async with INEVClient(
    api_key="your_key",
    batch_size=100,      # Flush every 100 events
    flush_interval=5.0   # Or every 5 seconds
) as client:
    # Events batched automatically
    for order in orders:
        await client.emit(entity="order", action="process")
```

## What Gets Captured?

Every event includes:

```python
{
    "event_id": "uuid4",           # Auto-generated
    "timestamp": "2024-01-01T...", # Auto-generated
    "entity": "order",             # Your entity
    "action": "create",            # Your action
    "record_id": "order_123",      # Optional
    "from_state": "pending",       # Optional
    "to_state": "shipped",         # Optional
    "outcome": "success",          # Auto-set
    "user_id": "user_456",         # Optional
    "parameters": {...},           # Optional metadata
    "environment": "production"    # From config
}
```

## Configuration Options

```python
client = INEVClient(
    api_key="your_key",           # Required
    base_url="https://api.inev.io",  # Default
    environment="production",      # Default
    auto_batch=True,              # Enable batching
    batch_size=100,               # Batch size
    flush_interval=5.0,           # Flush interval (seconds)
    sync_mode=False               # Sync mode for serverless
)
```

## Next Steps

- See [README.md](README.md) for comprehensive examples
- See [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for technical details
- Run examples: `python examples/basic_usage.py`
- Run tests: `pytest tests/ -v`

## Need Help?

- Documentation: See README.md
- Examples: See examples/basic_usage.py
- Tests: See tests/test_client.py

## License

MIT
