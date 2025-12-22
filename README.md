# INEV SDK for Python

The INEV SDK provides **automatic event capture** for Intentionality Leakage Analysis (ILA). Track user behavior, detect trajectory gaps, and identify error leaks with minimal code changes.

## Installation

```bash
pip install inev-sdk
```

## Quick Start

### Auto-Instrumentation (Recommended)

The easiest way to get started is with **zero-code auto-instrumentation** using middleware:

```python
from fastapi import FastAPI
from inev_sdk.integrations.fastapi import INEVMiddleware

app = FastAPI()

# Add middleware - that's it! All API calls are now tracked automatically
app.add_middleware(
    INEVMiddleware,
    api_key="sk_live_...",
    project_id="proj_123",
    excluded_paths=["/health", "/docs"],  # Optional: paths to skip
)
```

**What this captures:**
- All HTTP requests/responses automatically
- Action names derived from HTTP method + path (e.g., `post_orders`, `get_users`)
- Success/error outcomes based on status codes
- Request duration, parameters, user context
- Non-blocking event batching (never slows down requests)

**Server-side enrichment:**
Configure entity/state mappings in the INEV dashboard, and the server will automatically enrich your events with domain context. No code changes needed! This is **Tier 1 of Hybrid Event Capture** - zero-code instrumentation with server-side intelligence.

### Manual Instrumentation (For Custom Events)

For business events that aren't tied to HTTP endpoints, use the SDK directly:

```python
import asyncio
from inev_sdk import INEVClient

async def main():
    async with INEVClient(api_key="sk_live_...") as client:
        # Emit a domain event
        event_id = await client.emit(
            entity="order",
            action="create",
            record_id="order_123",
            to_state="pending",
            user_id="user_456",
            parameters={"total": 99.99}
        )
        print(f"Event emitted: {event_id}")

asyncio.run(main())
```

## Middleware Configuration

The middleware accepts the following configuration options:

```python
app.add_middleware(
    INEVMiddleware,
    api_key="sk_live_...",              # Required: INEV API key
    project_id="proj_123",              # Required: Project to associate events with
    endpoint="https://api.inev.io",     # Optional: API endpoint (default: production)
    excluded_paths=["/health", "/docs"],  # Optional: paths to skip monitoring
    auto_enrich=True,                   # Optional: enable server-side enrichment (default: True)
    batch_size=100,                     # Optional: events per batch (default: 100)
    flush_interval=5.0,                 # Optional: flush interval in seconds (default: 5.0)
    environment="production",           # Optional: environment tag (default: "production")
)
```

**Framework Support:**
- **FastAPI/Starlette**: Full support (async)
- **Django**: Coming soon (see stub implementation)
- **Flask**: Coming soon (see stub implementation)

## Features

### Auto-Instrumentation Middleware

The middleware provides **zero-code instrumentation** for your FastAPI application:

1. **Automatic Action Extraction**: Converts HTTP requests to semantic actions
   - `POST /api/v1/orders` → `post_orders`
   - `GET /api/v1/users/123` → `get_users`
   - `PATCH /api/v1/orders/456` → `patch_orders`

2. **Smart User Identification**: Extracts user context from multiple sources
   - `request.state.user_id` (set by auth middleware)
   - `X-User-ID` header
   - `X-API-Key` header (masked for privacy)
   - `Authorization` header (masked)
   - Session cookies

3. **Source Detection**: Identifies request origin
   - Frontend (via `X-Client-Type: frontend`)
   - Mobile apps (via User-Agent)
   - API clients (via User-Agent)
   - Browsers

4. **Non-Blocking Performance**:
   - Events are queued and batched asynchronously
   - Never slows down request processing
   - Configurable batch size and flush interval
   - Graceful degradation if queue is full

5. **Path Exclusions**: Skip monitoring for health checks, docs, etc.
   - Defaults: `/health`, `/ready`, `/metrics`, `/docs`, `/openapi.json`, `/redoc`
   - Fully customizable via `excluded_paths`

### Automatic Batching

The SDK automatically batches events for improved performance:

```python
async with INEVClient(
    api_key="your_api_key",
    batch_size=100,        # Flush after 100 events
    flush_interval=5.0     # Or after 5 seconds
) as client:
    # Events are batched automatically
    for i in range(200):
        await client.emit(entity="order", action="process")

    # Explicit flush if needed
    await client.flush()
```

### Decorator Pattern

Automatically emit events after function execution:

```python
from inev_sdk import emit_domain_event, configure

configure(api_key="your_api_key")

@emit_domain_event(
    entity="order",
    action="create",
    record_id_attr="id",
    state_attr="status"
)
async def create_order(data):
    order = Order(id=data["id"], status="pending")
    # ... save to database ...
    return order

# Event is automatically emitted after function completes
order = await create_order({"id": "order_123"})
```

### Context Manager for State Transitions

Track state transitions with automatic error handling:

```python
from inev_sdk import InstrumentationContext, INEVClient

async with INEVClient(api_key="your_api_key") as client:
    async with InstrumentationContext(
        entity="order",
        record_id="order_123",
        from_state="pending",
        client=client
    ) as ctx:
        # Perform state transition
        await process_payment(order)
        ctx.set_to_state("paid")

        # If an exception occurs, it's automatically captured
        # and the event is marked as outcome="error"
```

### Synchronous Mode (for Serverless)

For environments where async isn't suitable (e.g., AWS Lambda):

```python
from inev_sdk import INEVClient

client = INEVClient(api_key="your_api_key", sync_mode=True)

def lambda_handler(event, context):
    # Use synchronous emit
    event_id = client.emit_sync(
        entity="order",
        action="process",
        record_id=event["order_id"]
    )
    return {"statusCode": 200, "body": f"Event: {event_id}"}
```

## Advanced Usage

### State Transitions

Capture complete state machine transitions:

```python
await client.emit(
    entity="order",
    action="ship",
    record_id="order_123",
    from_state="pending",
    to_state="shipped",
    user_id="user_456",
    parameters={
        "shipping_carrier": "UPS",
        "tracking_number": "1Z999AA10123456784"
    }
)
```

### Error Tracking

Track errors and outcomes:

```python
async with InstrumentationContext(
    entity="payment",
    record_id="pay_123",
    from_state="pending",
    client=client
) as ctx:
    try:
        result = await process_payment()
        ctx.set_to_state("completed")
    except PaymentError as e:
        ctx.set_error(str(e))
        # Event will be marked with outcome="error"
        raise
```

### Custom Fields

Add custom metadata to events:

```python
await client.emit(
    entity="order",
    action="create",
    record_id="order_123",
    # Custom fields via kwargs
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0...",
    referrer="https://example.com",
    ab_test_variant="checkout_v2"
)
```

## Configuration Options

```python
client = INEVClient(
    api_key="your_api_key",
    base_url="https://api.inev.io",  # API endpoint
    environment="production",         # Environment tag
    auto_batch=True,                  # Enable batching
    batch_size=100,                   # Batch size threshold
    flush_interval=5.0,               # Time-based flush (seconds)
    sync_mode=False                   # Enable sync methods
)
```

## Event Schema

Each event contains:

- `event_id`: Unique identifier (UUID)
- `timestamp`: ISO 8601 timestamp
- `entity`: Entity type (e.g., "order", "payment")
- `action`: Action performed (e.g., "create", "update", "ship")
- `record_id`: Record identifier (optional)
- `from_state`: Previous state (optional)
- `to_state`: New state (optional)
- `outcome`: "success" or "error"
- `error_message`: Error details (optional)
- `user_id`: User identifier (optional)
- `session_id`: Session identifier (optional)
- `parameters`: Custom parameters (dict)
- `environment`: Environment tag
- Additional custom fields via kwargs

## Best Practices

1. **Use context managers**: Always use `async with` for automatic cleanup
2. **Configure globally**: Set up once at startup, reuse everywhere
3. **Batch for performance**: Enable batching for high-volume scenarios
4. **Track state transitions**: Include from_state and to_state for trajectory analysis
5. **Capture errors**: Use InstrumentationContext for automatic error tracking
6. **Add context**: Use parameters and custom fields for rich event data

## Testing

```python
import pytest
from unittest.mock import AsyncMock, patch
from inev_sdk import INEVClient

@pytest.mark.asyncio
async def test_event_emission():
    async with INEVClient(api_key="test_key", auto_batch=False) as client:
        with patch.object(client, '_send', new_callable=AsyncMock) as mock_send:
            event_id = await client.emit(
                entity="order",
                action="create",
                record_id="order_123"
            )
            assert event_id
            mock_send.assert_called_once()
```

## License

MIT
