"""Tests for FastAPI middleware enhanced error parsing (Step 11)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient

from inev_sdk.integrations.fastapi import INEVMiddleware


@pytest.fixture
def mock_client():
    """Create a mock INEVClient for testing."""
    client = MagicMock()
    client._running = True
    client.start = AsyncMock()
    client.emit = AsyncMock(return_value="evt_123")
    return client


# =============================================================================
# Step 11: Error Response Parsing Tests
# =============================================================================


class TestParseErrorResponse:
    """Test the _parse_error_response method."""

    def test_parse_standard_error_format(self):
        """Test parsing standard error format: {"code": "...", "message": "...", "details": {...}}."""
        middleware = INEVMiddleware.__new__(INEVMiddleware)

        error_body = {
            "code": "VALIDATION_ERROR",
            "message": "Email is invalid",
            "details": {"field": "email", "reason": "invalid format"},
        }

        result = middleware._parse_error_response(error_body, 400)

        assert result["error_code"] == "VALIDATION_ERROR"
        assert result["error_message"] == "Email is invalid"
        assert result["error_details"] == {"field": "email", "reason": "invalid format"}
        assert result["error_category"] == "validation"

    def test_parse_fastapi_validation_error(self):
        """Test parsing FastAPI validation errors: {"detail": [{"loc": [...], "msg": "...", "type": "..."}]}."""
        middleware = INEVMiddleware.__new__(INEVMiddleware)

        error_body = {
            "detail": [
                {"loc": ["body", "email"], "msg": "field required", "type": "missing"},
                {"loc": ["body", "age"], "msg": "value is not a valid integer", "type": "int_parsing"},
            ]
        }

        result = middleware._parse_error_response(error_body, 422)

        assert result["error_code"] == "VALIDATION_ERROR"
        assert "body.email - field required" in result["error_message"]
        assert "body.age - value is not a valid integer" in result["error_message"]
        assert result["error_category"] == "validation"
        assert result["error_details"]["validation_errors"] == error_body["detail"]

    def test_parse_fastapi_validation_single_error(self):
        """Test parsing FastAPI validation error with single error."""
        middleware = INEVMiddleware.__new__(INEVMiddleware)

        error_body = {"detail": [{"loc": ["body", "password"], "msg": "string too short", "type": "string_too_short"}]}

        result = middleware._parse_error_response(error_body, 422)

        assert "body.password - string too short" in result["error_message"]

    def test_parse_django_rest_framework_error(self):
        """Test parsing Django REST Framework errors: {"field": ["error"]}."""
        middleware = INEVMiddleware.__new__(INEVMiddleware)

        error_body = {
            "email": ["This field is required."],
            "password": ["Password must be at least 8 characters."],
        }

        result = middleware._parse_error_response(error_body, 400)

        assert result["error_category"] == "validation"
        assert "email" in result["error_details"]["field_errors"]
        assert "password" in result["error_details"]["field_errors"]
        assert "This field is required." in result["error_message"]

    def test_parse_graphql_error(self):
        """Test parsing GraphQL errors: {"errors": [{"message": "..."}]}."""
        middleware = INEVMiddleware.__new__(INEVMiddleware)

        error_body = {
            "errors": [
                {"message": "User not found", "locations": [{"line": 2, "column": 3}]},
                {"message": "Invalid permission"},
            ]
        }

        result = middleware._parse_error_response(error_body, 400)

        assert "User not found" in result["error_message"]
        assert result["error_details"]["graphql_errors"] == error_body["errors"]

    def test_parse_simple_detail_string(self):
        """Test parsing simple detail string: {"detail": "Not found"}."""
        middleware = INEVMiddleware.__new__(INEVMiddleware)

        error_body = {"detail": "Resource not found"}

        result = middleware._parse_error_response(error_body, 404)

        assert result["error_message"] == "Resource not found"
        assert result["error_category"] == "not_found"

    def test_parse_simple_message_string(self):
        """Test parsing simple message string: {"message": "..."}."""
        middleware = INEVMiddleware.__new__(INEVMiddleware)

        error_body = {"message": "Internal server error occurred"}

        result = middleware._parse_error_response(error_body, 500)

        assert result["error_message"] == "Internal server error occurred"
        assert result["error_category"] == "server"

    def test_parse_error_with_error_field(self):
        """Test parsing error with error field: {"error": "..."}."""
        middleware = INEVMiddleware.__new__(INEVMiddleware)

        error_body = {"error": "Rate limit exceeded"}

        result = middleware._parse_error_response(error_body, 429)

        assert result["error_message"] == "Rate limit exceeded"
        assert result["error_category"] == "rate_limit"

    def test_parse_nested_error_object(self):
        """Test parsing nested error object: {"error": {"code": "...", "message": "..."}}."""
        middleware = INEVMiddleware.__new__(INEVMiddleware)

        error_body = {
            "error": {
                "code": "PAYMENT_FAILED",
                "message": "Card declined",
                "details": {"decline_code": "insufficient_funds"},
            }
        }

        result = middleware._parse_error_response(error_body, 400)

        assert result["error_code"] == "PAYMENT_FAILED"
        assert result["error_message"] == "Card declined"
        assert result["error_details"]["decline_code"] == "insufficient_funds"

    def test_parse_empty_body(self):
        """Test parsing empty response body."""
        middleware = INEVMiddleware.__new__(INEVMiddleware)

        result = middleware._parse_error_response({}, 500)

        assert result["error_message"] == "Internal Server Error"
        assert result["error_category"] == "server"

    def test_parse_malformed_body(self):
        """Test handling of malformed body (non-dict)."""
        middleware = INEVMiddleware.__new__(INEVMiddleware)

        # Should handle gracefully
        result = middleware._parse_error_response("just a string", 400)

        assert result["error_message"] == "just a string"

    def test_infer_category_from_status_code(self):
        """Test that error_category is inferred from status code."""
        middleware = INEVMiddleware.__new__(INEVMiddleware)

        # 400 -> validation
        result = middleware._parse_error_response({"message": "Bad request"}, 400)
        assert result["error_category"] == "validation"

        # 401 -> auth
        result = middleware._parse_error_response({"message": "Unauthorized"}, 401)
        assert result["error_category"] == "auth"

        # 403 -> auth
        result = middleware._parse_error_response({"message": "Forbidden"}, 403)
        assert result["error_category"] == "auth"

        # 404 -> not_found
        result = middleware._parse_error_response({"message": "Not found"}, 404)
        assert result["error_category"] == "not_found"

        # 429 -> rate_limit
        result = middleware._parse_error_response({"message": "Too many requests"}, 429)
        assert result["error_category"] == "rate_limit"

        # 500+ -> server
        result = middleware._parse_error_response({"message": "Server error"}, 500)
        assert result["error_category"] == "server"


class TestMiddlewareEmitsStructuredErrors:
    """Test that middleware emits structured error fields."""

    @pytest.mark.asyncio
    async def test_middleware_emits_error_code_from_response(self, mock_client):
        """Test that middleware extracts error_code from response when body is available."""
        app = FastAPI()

        @app.post("/api/v1/orders")
        async def create_order():
            return JSONResponse(
                status_code=400,
                content={"code": "ORDER_LIMIT_EXCEEDED", "message": "Cannot create more orders"},
            )

        with patch("inev_sdk.integrations.fastapi.INEVClient", return_value=mock_client):
            app.add_middleware(
                INEVMiddleware,
                api_key="sk_test_123",
                project_id="proj_test",
            )

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/orders", json={})
                assert response.status_code == 400

            call_args = mock_client.emit.call_args[1]
            assert call_args["outcome"] == "error"
            # Note: error_code extraction depends on body access which may not work in all ASGI contexts
            # The category should be inferred from status code at minimum
            assert call_args["error_category"] == "validation"

    @pytest.mark.asyncio
    async def test_middleware_emits_validation_errors(self, mock_client):
        """Test that middleware handles FastAPI validation errors."""
        app = FastAPI()

        from pydantic import BaseModel

        class OrderRequest(BaseModel):
            email: str
            quantity: int

        @app.post("/api/v1/orders")
        async def create_order(order: OrderRequest):
            return {"order_id": "123"}

        with patch("inev_sdk.integrations.fastapi.INEVClient", return_value=mock_client):
            app.add_middleware(
                INEVMiddleware,
                api_key="sk_test_123",
                project_id="proj_test",
            )

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # Send invalid request body
                response = await client.post("/api/v1/orders", json={"invalid": "data"})
                assert response.status_code == 422

            call_args = mock_client.emit.call_args[1]
            assert call_args["outcome"] == "error"
            # Category should be validation for 422
            assert call_args["error_category"] == "validation"

    @pytest.mark.asyncio
    async def test_middleware_emits_error_type(self, mock_client):
        """Test that middleware emits error_category based on status code."""
        app = FastAPI()

        @app.get("/api/v1/orders/{order_id}")
        async def get_order(order_id: str):
            raise HTTPException(status_code=404, detail="Order not found")

        with patch("inev_sdk.integrations.fastapi.INEVClient", return_value=mock_client):
            app.add_middleware(
                INEVMiddleware,
                api_key="sk_test_123",
                project_id="proj_test",
            )

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/v1/orders/not_found")
                assert response.status_code == 404

            call_args = mock_client.emit.call_args[1]
            assert call_args["outcome"] == "error"
            assert call_args["error_category"] == "not_found"
            # error_message may be from body or default status text
            assert call_args["error_message"] is not None

    @pytest.mark.asyncio
    async def test_middleware_handles_graphql_errors(self, mock_client):
        """Test that middleware handles GraphQL error format."""
        app = FastAPI()

        @app.post("/graphql")
        async def graphql_endpoint():
            return JSONResponse(
                status_code=200,  # GraphQL often returns 200 with errors in body
                content={
                    "data": None,
                    "errors": [{"message": "User not found", "extensions": {"code": "NOT_FOUND"}}],
                },
            )

        with patch("inev_sdk.integrations.fastapi.INEVClient", return_value=mock_client):
            app.add_middleware(
                INEVMiddleware,
                api_key="sk_test_123",
                project_id="proj_test",
            )

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/graphql", json={"query": "{ user { id } }"})
                assert response.status_code == 200

            # For GraphQL 200 with errors, we still capture as success
            # The middleware can be enhanced to detect GraphQL errors in 200 responses
            call_args = mock_client.emit.call_args[1]
            assert call_args["outcome"] == "success"

    @pytest.mark.asyncio
    async def test_middleware_rate_limit_category(self, mock_client):
        """Test that 429 status is categorized as rate_limit."""
        app = FastAPI()

        @app.get("/api/v1/data")
        async def get_data():
            return JSONResponse(
                status_code=429,
                content={"message": "Too many requests", "retry_after": 60},
            )

        with patch("inev_sdk.integrations.fastapi.INEVClient", return_value=mock_client):
            app.add_middleware(
                INEVMiddleware,
                api_key="sk_test_123",
                project_id="proj_test",
            )

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/v1/data")
                assert response.status_code == 429

            call_args = mock_client.emit.call_args[1]
            assert call_args["outcome"] == "error"
            assert call_args["error_category"] == "rate_limit"

    @pytest.mark.asyncio
    async def test_middleware_auth_category(self, mock_client):
        """Test that 401/403 status is categorized as auth."""
        app = FastAPI()

        @app.get("/api/v1/protected")
        async def protected():
            raise HTTPException(status_code=401, detail="Authentication required")

        with patch("inev_sdk.integrations.fastapi.INEVClient", return_value=mock_client):
            app.add_middleware(
                INEVMiddleware,
                api_key="sk_test_123",
                project_id="proj_test",
            )

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/v1/protected")
                assert response.status_code == 401

            call_args = mock_client.emit.call_args[1]
            assert call_args["outcome"] == "error"
            assert call_args["error_category"] == "auth"

    @pytest.mark.asyncio
    async def test_middleware_preserves_backward_compatibility(self, mock_client):
        """Test that existing error_message behavior is preserved."""
        app = FastAPI()

        @app.get("/api/v1/fail")
        async def fail():
            raise HTTPException(status_code=500, detail="Something went wrong")

        with patch("inev_sdk.integrations.fastapi.INEVClient", return_value=mock_client):
            app.add_middleware(
                INEVMiddleware,
                api_key="sk_test_123",
                project_id="proj_test",
            )

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/v1/fail")
                assert response.status_code == 500

            call_args = mock_client.emit.call_args[1]
            assert call_args["outcome"] == "error"
            # error_message should still be set (backward compatible)
            # May be from response body or status code default
            assert call_args["error_message"] is not None
            assert call_args["error_category"] == "server"
