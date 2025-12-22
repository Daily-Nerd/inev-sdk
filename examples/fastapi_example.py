"""
Example FastAPI application with INEV auto-instrumentation.

This demonstrates how to add the INEVMiddleware to automatically capture
all API requests/responses as domain events for ILA analysis.

Run with:
    uvicorn examples.fastapi_example:app --reload
"""

from fastapi import FastAPI, HTTPException
from inev_sdk.integrations.fastapi import INEVMiddleware
from pydantic import BaseModel


# Create FastAPI app
app = FastAPI(title="Order Management API")


# Add INEV middleware for automatic event capture
app.add_middleware(
    INEVMiddleware,
    api_key="sk_test_your_api_key_here",  # Replace with your actual API key
    project_id="proj_your_project_id",  # Replace with your project ID
    excluded_paths=["/health", "/docs", "/openapi.json"],
    auto_enrich=True,  # Enable server-side enrichment
    environment="development",
)


# Data models
class OrderCreate(BaseModel):
    item: str
    quantity: int
    price: float


class Order(BaseModel):
    id: str
    item: str
    quantity: int
    price: float
    status: str


# In-memory storage for demo
orders = {}
order_counter = 0


@app.get("/health")
async def health():
    """Health check endpoint (excluded from monitoring)."""
    return {"status": "ok"}


@app.get("/api/v1/orders")
async def list_orders():
    """List all orders."""
    return {"orders": list(orders.values())}


@app.post("/api/v1/orders")
async def create_order(order: OrderCreate):
    """Create a new order.

    This will be captured as action="post_orders" with to_state="created"
    (if server-side enrichment is configured).
    """
    global order_counter
    order_counter += 1
    order_id = f"order_{order_counter}"

    new_order = Order(
        id=order_id,
        item=order.item,
        quantity=order.quantity,
        price=order.price,
        status="pending",
    )
    orders[order_id] = new_order

    return new_order


@app.get("/api/v1/orders/{order_id}")
async def get_order(order_id: str):
    """Get a specific order.

    This will be captured as action="get_orders".
    """
    if order_id not in orders:
        raise HTTPException(status_code=404, detail="Order not found")

    return orders[order_id]


@app.patch("/api/v1/orders/{order_id}")
async def update_order(order_id: str, status: str):
    """Update order status.

    This will be captured as action="patch_orders" with state transition
    (if server-side enrichment is configured).
    """
    if order_id not in orders:
        raise HTTPException(status_code=404, detail="Order not found")

    order = orders[order_id]
    old_status = order.status
    order.status = status

    return {"id": order_id, "old_status": old_status, "new_status": status}


@app.delete("/api/v1/orders/{order_id}")
async def cancel_order(order_id: str):
    """Cancel an order.

    This will be captured as action="delete_orders" with to_state="cancelled"
    (if server-side enrichment is configured).
    """
    if order_id not in orders:
        raise HTTPException(status_code=404, detail="Order not found")

    orders[order_id].status = "cancelled"

    return {"message": "Order cancelled", "id": order_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
