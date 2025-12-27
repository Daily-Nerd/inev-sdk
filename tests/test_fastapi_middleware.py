"""Tests for FastAPI auto-instrumentation middleware."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
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


@pytest.fixture
def test_app():
    """Create a test FastAPI app."""
    app = FastAPI()

    @app.get("/api/v1/users")
    async def get_users():
        return {"users": []}

    @app.post("/api/v1/orders")
    async def create_order():
        return {"order_id": "order_123"}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/v1/orders/{order_id}")
    async def get_order(order_id: str):
        if order_id == "not_found":
            raise HTTPException(status_code=404, detail="Order not found")
        return {"order_id": order_id}

    return app


@pytest.mark.asyncio
async def test_middleware_captures_successful_request(mock_client):
    """Test that middleware captures successful API requests."""
    app = FastAPI()

    @app.get("/api/v1/users")
    async def get_users():
        return {"users": []}

    with patch("inev_sdk.integrations.fastapi.INEVClient", return_value=mock_client):
        app.add_middleware(
            INEVMiddleware,
            api_key="sk_test_123",
            project_id="proj_test",
            excluded_paths=["/health"],
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/users")
            assert response.status_code == 200

        # Verify event was emitted
        assert mock_client.emit.called
        call_args = mock_client.emit.call_args[1]

        assert call_args["action"] == "get_users"
        assert call_args["outcome"] == "success"
        assert call_args["error_message"] is None
        assert call_args["parameters"]["method"] == "GET"
        assert call_args["parameters"]["path"] == "/api/v1/users"
        assert call_args["parameters"]["status_code"] == 200


@pytest.mark.asyncio
async def test_middleware_captures_error_request(mock_client):
    """Test that middleware captures failed requests."""
    app = FastAPI()

    @app.get("/api/v1/orders/{order_id}")
    async def get_order(order_id: str):
        if order_id == "not_found":
            raise HTTPException(status_code=404, detail="Order not found")
        return {"order_id": order_id}

    with patch("inev_sdk.integrations.fastapi.INEVClient", return_value=mock_client):
        app.add_middleware(
            INEVMiddleware,
            api_key="sk_test_123",
            project_id="proj_test",
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/orders/not_found")
            assert response.status_code == 404

        # Verify event was emitted with error
        assert mock_client.emit.called
        call_args = mock_client.emit.call_args[1]

        # With semantic naming, /orders/not_found becomes get_order (singular, not_found is treated as ID-like)
        assert call_args["action"] == "get_order"
        assert call_args["outcome"] == "error"
        # Error message now includes response body details
        assert "Not Found" in call_args["error_message"] or call_args["error_message"] == "Not Found"
        assert call_args["parameters"]["status_code"] == 404


@pytest.mark.asyncio
async def test_middleware_skips_excluded_paths(mock_client):
    """Test that excluded paths are not monitored."""
    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    with patch("inev_sdk.integrations.fastapi.INEVClient", return_value=mock_client):
        app.add_middleware(
            INEVMiddleware,
            api_key="sk_test_123",
            project_id="proj_test",
            excluded_paths=["/health"],
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200

        # Verify NO event was emitted
        mock_client.emit.assert_not_called()


@pytest.mark.asyncio
async def test_middleware_extracts_user_id_from_header(mock_client):
    """Test that user_id is extracted from X-User-ID header."""
    app = FastAPI()

    @app.get("/api/v1/users")
    async def get_users():
        return {"users": []}

    with patch("inev_sdk.integrations.fastapi.INEVClient", return_value=mock_client):
        app.add_middleware(
            INEVMiddleware,
            api_key="sk_test_123",
            project_id="proj_test",
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/users", headers={"X-User-ID": "user_123"})
            assert response.status_code == 200

        call_args = mock_client.emit.call_args[1]
        assert call_args["user_id"] == "user_123"


@pytest.mark.asyncio
async def test_middleware_extracts_session_id(mock_client):
    """Test that session_id is extracted from headers."""
    app = FastAPI()

    @app.get("/api/v1/users")
    async def get_users():
        return {"users": []}

    with patch("inev_sdk.integrations.fastapi.INEVClient", return_value=mock_client):
        app.add_middleware(
            INEVMiddleware,
            api_key="sk_test_123",
            project_id="proj_test",
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/users", headers={"X-Session-ID": "sess_abc123"})
            assert response.status_code == 200

        call_args = mock_client.emit.call_args[1]
        assert call_args["session_id"] == "sess_abc123"


@pytest.mark.asyncio
async def test_middleware_includes_duration(mock_client):
    """Test that request duration is captured."""
    app = FastAPI()

    @app.get("/api/v1/users")
    async def get_users():
        return {"users": []}

    with patch("inev_sdk.integrations.fastapi.INEVClient", return_value=mock_client):
        app.add_middleware(
            INEVMiddleware,
            api_key="sk_test_123",
            project_id="proj_test",
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/users")
            assert response.status_code == 200

        call_args = mock_client.emit.call_args[1]
        assert "duration_ms" in call_args["parameters"]
        assert call_args["parameters"]["duration_ms"] >= 0


@pytest.mark.asyncio
async def test_middleware_includes_query_params(mock_client):
    """Test that query parameters are captured."""
    app = FastAPI()

    @app.get("/api/v1/users")
    async def get_users():
        return {"users": []}

    with patch("inev_sdk.integrations.fastapi.INEVClient", return_value=mock_client):
        app.add_middleware(
            INEVMiddleware,
            api_key="sk_test_123",
            project_id="proj_test",
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/users?page=2&limit=50")
            assert response.status_code == 200

        call_args = mock_client.emit.call_args[1]
        query_params = call_args["parameters"]["query_params"]
        assert query_params["page"] == "2"
        assert query_params["limit"] == "50"


@pytest.mark.asyncio
async def test_middleware_handles_post_requests(mock_client):
    """Test that POST requests are captured correctly."""
    app = FastAPI()

    @app.post("/api/v1/orders")
    async def create_order():
        return {"order_id": "order_123"}

    with patch("inev_sdk.integrations.fastapi.INEVClient", return_value=mock_client):
        app.add_middleware(
            INEVMiddleware,
            api_key="sk_test_123",
            project_id="proj_test",
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/orders", json={"item": "widget"})
            assert response.status_code == 200

        call_args = mock_client.emit.call_args[1]
        assert call_args["action"] == "post_orders"
        assert call_args["parameters"]["method"] == "POST"


# =============================================================================
# Action Extractor Tests
# =============================================================================


class TestActionExtractor:
    """Test the action extraction logic."""

    def test_simple_resource_path(self):
        """Test action extraction from simple resource path."""
        middleware = INEVMiddleware.__new__(INEVMiddleware)
        middleware.action_extractor = INEVMiddleware._default_action_extractor

        class MockRequest:
            method = "GET"

            class url:
                path = "/api/v1/users"

        action = middleware._default_action_extractor(MockRequest())
        assert action == "get_users"

    def test_nested_resource_path(self):
        """Test action extraction from nested resource path.

        The new semantic naming includes the full resource path,
        filtering out ID segments and singularizing where appropriate.
        """
        middleware = INEVMiddleware.__new__(INEVMiddleware)

        class MockRequest:
            method = "POST"

            class url:
                path = "/api/v1/users/123/orders"

        action = INEVMiddleware._default_action_extractor(middleware, MockRequest())
        # Semantic naming: users/{id}/orders -> user_orders (users is singularized before ID)
        assert action == "post_user_orders"

    def test_path_with_id_parameter(self):
        """Test that ID parameters are stripped and resource is singularized."""
        middleware = INEVMiddleware.__new__(INEVMiddleware)

        class MockRequest:
            method = "GET"

            class url:
                path = "/api/v1/orders/ord_abc123"

        action = INEVMiddleware._default_action_extractor(middleware, MockRequest())
        # When accessing a single resource by ID, the resource name is singularized
        assert action == "get_order"

    def test_root_path(self):
        """Test action extraction from root path."""
        middleware = INEVMiddleware.__new__(INEVMiddleware)

        class MockRequest:
            method = "GET"

            class url:
                path = "/"

        action = INEVMiddleware._default_action_extractor(middleware, MockRequest())
        assert action == "get_root"


# =============================================================================
# Default Excluded Paths Tests
# =============================================================================


class TestDefaultExcludedPaths:
    """Test default path exclusion behavior."""

    def test_default_excluded_paths_list(self):
        """Test that default excluded paths are set correctly."""
        expected = [
            "/health",
            "/ready",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/favicon.ico",
        ]
        assert expected == INEVMiddleware.DEFAULT_EXCLUDE_PATHS

    @pytest.mark.asyncio
    async def test_docs_excluded_by_default(self, mock_client):
        """Test that /docs is excluded by default."""
        app = FastAPI()

        @app.get("/docs")
        async def docs():
            return {"docs": "here"}

        with patch("inev_sdk.integrations.fastapi.INEVClient", return_value=mock_client):
            app.add_middleware(
                INEVMiddleware,
                api_key="sk_test_123",
                project_id="proj_test",
                # Not specifying excluded_paths uses defaults
            )

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                await client.get("/docs")

            # Should not have emitted an event
            mock_client.emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_metrics_excluded_by_default(self, mock_client):
        """Test that /metrics is excluded by default."""
        app = FastAPI()

        @app.get("/metrics")
        async def metrics():
            return {"metrics": "here"}

        with patch("inev_sdk.integrations.fastapi.INEVClient", return_value=mock_client):
            app.add_middleware(
                INEVMiddleware,
                api_key="sk_test_123",
                project_id="proj_test",
            )

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                await client.get("/metrics")

            mock_client.emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_custom_excluded_paths_override_defaults(self, mock_client):
        """Test that providing excluded_paths overrides defaults."""
        app = FastAPI()

        @app.get("/docs")
        async def docs():
            return {"docs": "here"}

        @app.get("/custom-skip")
        async def custom_skip():
            return {"skip": "this"}

        with patch("inev_sdk.integrations.fastapi.INEVClient", return_value=mock_client):
            # Custom paths - /docs is NOT excluded here
            app.add_middleware(
                INEVMiddleware,
                api_key="sk_test_123",
                project_id="proj_test",
                excluded_paths=["/custom-skip"],
            )

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # /docs should now be captured (not in custom exclusions)
                await client.get("/docs")
                assert mock_client.emit.called

                mock_client.emit.reset_mock()

                # /custom-skip should be excluded
                await client.get("/custom-skip")
                mock_client.emit.assert_not_called()
