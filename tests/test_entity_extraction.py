"""Tests for entity and record_id extraction from URL paths."""

from inev_sdk.utils.entity_extraction import (
    extract_entity_and_record_id,
    extract_parent_entity_and_id,
)


class TestExtractEntityAndRecordId:
    """Tests for extract_entity_and_record_id function."""

    def test_simple_resource_with_id(self):
        """Test simple resource path with ID."""
        entity, record_id = extract_entity_and_record_id("/api/v1/orders/123")
        assert entity == "order"
        assert record_id == "123"

    def test_simple_resource_collection(self):
        """Test simple resource collection (no ID)."""
        entity, record_id = extract_entity_and_record_id("/api/v1/orders")
        assert entity == "order"
        assert record_id is None

    def test_nested_resource(self):
        """Test nested resource path."""
        entity, record_id = extract_entity_and_record_id("/api/workspaces/ws_abc/members/usr_456")
        assert entity == "member"
        assert record_id == "usr_456"

    def test_resource_with_subresource(self):
        """Test resource with subresource (no ID on subresource)."""
        entity, record_id = extract_entity_and_record_id("/api/users/42/profile")
        assert entity == "user"
        assert record_id == "42"

    def test_uuid_id(self):
        """Test UUID as record ID."""
        entity, record_id = extract_entity_and_record_id("/api/orders/550e8400-e29b-41d4-a716-446655440000")
        assert entity == "order"
        assert record_id == "550e8400-e29b-41d4-a716-446655440000"

    def test_prefixed_id(self):
        """Test prefixed IDs like ws_123."""
        entity, record_id = extract_entity_and_record_id("/api/workspaces/ws_123")
        assert entity == "workspace"
        assert record_id == "ws_123"

    def test_no_api_prefix(self):
        """Test path without /api prefix."""
        entity, record_id = extract_entity_and_record_id("/orders/123")
        assert entity == "order"
        assert record_id == "123"

    def test_with_version(self):
        """Test path with version segment."""
        entity, record_id = extract_entity_and_record_id("/api/v2/users/456")
        assert entity == "user"
        assert record_id == "456"

    def test_trailing_slash(self):
        """Test path with trailing slash."""
        entity, record_id = extract_entity_and_record_id("/api/orders/123/")
        assert entity == "order"
        assert record_id == "123"

    def test_health_check_path(self):
        """Test non-resource paths like health checks."""
        entity, record_id = extract_entity_and_record_id("/health")
        assert entity == "health"
        assert record_id is None

    def test_empty_path(self):
        """Test empty path."""
        entity, record_id = extract_entity_and_record_id("")
        assert entity is None
        assert record_id is None

    def test_root_path(self):
        """Test root path."""
        entity, record_id = extract_entity_and_record_id("/")
        assert entity is None
        assert record_id is None

    def test_deeply_nested_resource(self):
        """Test deeply nested resource path."""
        entity, record_id = extract_entity_and_record_id("/api/projects/123/tasks/456/comments/789")
        assert entity == "comment"
        assert record_id == "789"

    def test_action_endpoint(self):
        """Test action endpoint (verb at end)."""
        entity, record_id = extract_entity_and_record_id("/api/orders/123/confirm")
        assert entity == "order"
        assert record_id == "123"


class TestExtractParentEntityAndId:
    """Tests for extract_parent_entity_and_id function."""

    def test_nested_resource(self):
        """Test extraction of parent from nested resource."""
        parent, parent_id = extract_parent_entity_and_id("/api/workspaces/ws_123/members/usr_456")
        assert parent == "workspace"
        assert parent_id == "ws_123"

    def test_no_parent(self):
        """Test resource without parent."""
        parent, parent_id = extract_parent_entity_and_id("/api/orders/123")
        assert parent is None
        assert parent_id is None

    def test_collection_path(self):
        """Test collection path (no IDs)."""
        parent, parent_id = extract_parent_entity_and_id("/api/orders")
        assert parent is None
        assert parent_id is None

    def test_deeply_nested(self):
        """Test deeply nested - should return first parent."""
        parent, parent_id = extract_parent_entity_and_id("/api/projects/123/tasks/456/comments/789")
        assert parent == "project"
        assert parent_id == "123"

    def test_empty_path(self):
        """Test empty path."""
        parent, parent_id = extract_parent_entity_and_id("")
        assert parent is None
        assert parent_id is None


class TestRealWorldPaths:
    """Test real-world API path patterns."""

    def test_ecommerce_order_items(self):
        """Test e-commerce order items path."""
        entity, record_id = extract_entity_and_record_id("/api/v1/orders/ord_123/items/item_456")
        assert entity == "item"
        assert record_id == "item_456"

    def test_workspace_project_members(self):
        """Test SaaS workspace project path."""
        entity, record_id = extract_entity_and_record_id("/api/workspaces/ws_abc/projects/proj_xyz")
        assert entity == "project"
        assert record_id == "proj_xyz"

    def test_user_settings(self):
        """Test user settings path."""
        entity, record_id = extract_entity_and_record_id("/api/users/123/settings")
        assert entity == "user"
        assert record_id == "123"

    def test_payment_refund(self):
        """Test payment action path."""
        entity, record_id = extract_entity_and_record_id("/api/payments/pay_123/refund")
        assert entity == "payment"
        assert record_id == "pay_123"
