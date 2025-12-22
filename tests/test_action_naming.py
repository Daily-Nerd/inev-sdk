"""Tests for semantic action name generation."""

from inev_sdk.utils.action_naming import (
    generate_action_name,
    generate_semantic_action_name,
    is_id_segment,
    singularize,
)


class TestIsIdSegment:
    """Tests for ID segment detection."""

    def test_uuid_detection(self):
        """Test UUID detection."""
        assert is_id_segment("550e8400-e29b-41d4-a716-446655440000")
        assert is_id_segment("550E8400-E29B-41D4-A716-446655440000")  # uppercase

    def test_numeric_id_detection(self):
        """Test numeric ID detection."""
        assert is_id_segment("123")
        assert is_id_segment("999999")
        assert is_id_segment("1")

    def test_prefixed_id_detection(self):
        """Test prefixed ID detection (e.g., ws_123, proj_abc)."""
        assert is_id_segment("ws_123")
        assert is_id_segment("proj_abc123")
        assert is_id_segment("usr_xyz789")
        assert is_id_segment("u_1")  # short prefix

    def test_placeholder_detection(self):
        """Test placeholder parameter detection."""
        assert is_id_segment("{id}")
        assert is_id_segment("{user_id}")
        assert is_id_segment("{workspace_id}")

    def test_non_id_segments(self):
        """Test that regular segments are not detected as IDs."""
        assert not is_id_segment("users")
        assert not is_id_segment("workspaces")
        assert not is_id_segment("members")
        assert not is_id_segment("status")
        assert not is_id_segment("orders")

    def test_empty_segment(self):
        """Test empty segment handling."""
        assert is_id_segment("")


class TestSingularize:
    """Tests for singularization."""

    def test_regular_plurals(self):
        """Test regular -s plurals."""
        assert singularize("users") == "user"
        assert singularize("orders") == "order"
        assert singularize("projects") == "project"
        assert singularize("members") == "member"

    def test_ies_plurals(self):
        """Test -ies -> -y plurals."""
        assert singularize("categories") == "category"
        assert singularize("companies") == "company"
        assert singularize("entries") == "entry"

    def test_es_plurals(self):
        """Test -es plurals for words ending in s, x, z, ch, sh."""
        assert singularize("boxes") == "box"
        assert singularize("watches") == "watch"
        assert singularize("dishes") == "dish"
        assert singularize("statuses") == "status"

    def test_unchanged_words(self):
        """Test words that shouldn't change."""
        assert singularize("status") == "status"
        assert singularize("class") == "class"  # ends in ss
        assert singularize("us") == "us"  # too short


class TestGenerateActionName:
    """Tests for generate_action_name function."""

    def test_simple_resource(self):
        """Test simple resource path."""
        assert generate_action_name("GET", "/api/users") == "get_users"
        assert generate_action_name("POST", "/api/orders") == "post_orders"

    def test_resource_with_id(self):
        """Test resource with ID parameter."""
        assert generate_action_name("GET", "/api/users/123") == "get_user"
        assert generate_action_name("DELETE", "/api/orders/456") == "delete_order"

    def test_nested_resources(self):
        """Test nested resource paths."""
        assert generate_action_name("POST", "/api/workspaces/123/members") == "post_workspace_members"
        assert generate_action_name("GET", "/api/users/123/orders") == "get_user_orders"

    def test_deeply_nested(self):
        """Test deeply nested resource paths."""
        assert generate_action_name("POST", "/api/projects/123/tasks/456/comments") == "post_project_task_comments"

    def test_placeholder_parameters(self):
        """Test paths with placeholder parameters like {id}."""
        assert generate_action_name("GET", "/api/users/{id}") == "get_user"
        assert generate_action_name("POST", "/api/workspaces/{workspace_id}/members") == "post_workspace_members"

    def test_uuid_in_path(self):
        """Test paths with UUIDs."""
        assert generate_action_name("GET", "/api/users/550e8400-e29b-41d4-a716-446655440000") == "get_user"
        assert (
            generate_action_name("POST", "/api/workspaces/550e8400-e29b-41d4-a716-446655440000/members")
            == "post_workspace_members"
        )

    def test_prefixed_ids_in_path(self):
        """Test paths with prefixed IDs like ws_123."""
        assert generate_action_name("GET", "/api/workspaces/ws_123") == "get_workspace"
        assert generate_action_name("POST", "/api/projects/proj_abc/tasks") == "post_project_tasks"

    def test_version_removal(self):
        """Test that version segments are removed."""
        assert generate_action_name("GET", "/api/v1/users") == "get_users"
        assert generate_action_name("POST", "/api/v2/orders") == "post_orders"

    def test_no_api_prefix(self):
        """Test paths without /api prefix."""
        assert generate_action_name("GET", "/users") == "get_users"
        assert generate_action_name("POST", "/workspaces/ws_123/members") == "post_workspace_members"

    def test_trailing_slash(self):
        """Test paths with trailing slash."""
        assert generate_action_name("GET", "/api/users/") == "get_users"
        assert generate_action_name("POST", "/api/workspaces/ws_123/members/") == "post_workspace_members"

    def test_root_path(self):
        """Test root path."""
        assert generate_action_name("GET", "/") == "get_root"
        assert generate_action_name("GET", "/api") == "get_root"
        assert generate_action_name("GET", "/api/") == "get_root"

    def test_all_ids_path(self):
        """Test path with all ID segments."""
        # When all segments are IDs, should still produce something reasonable
        result = generate_action_name("GET", "/123/456")
        assert result.startswith("get_")


class TestGenerateSemanticActionName:
    """Tests for generate_semantic_action_name function."""

    def test_get_collection(self):
        """Test GET on collection uses 'list'."""
        assert generate_semantic_action_name("GET", "/api/users") == "list_users"
        assert generate_semantic_action_name("GET", "/api/orders") == "list_orders"

    def test_get_single_resource(self):
        """Test GET on single resource uses 'get'."""
        assert generate_semantic_action_name("GET", "/api/users/123") == "get_user"
        assert generate_semantic_action_name("GET", "/api/orders/456") == "get_order"

    def test_post_creates(self):
        """Test POST uses 'create' for top-level resources."""
        assert generate_semantic_action_name("POST", "/api/users") == "create_users"
        assert generate_semantic_action_name("POST", "/api/orders") == "create_orders"

    def test_post_adds_nested(self):
        """Test POST uses 'add' for nested resources."""
        assert generate_semantic_action_name("POST", "/api/workspaces/123/members") == "add_workspace_members"
        assert generate_semantic_action_name("POST", "/api/users/123/orders") == "add_user_orders"

    def test_patch_updates(self):
        """Test PATCH uses 'update'."""
        assert generate_semantic_action_name("PATCH", "/api/users/123") == "update_user"
        assert generate_semantic_action_name("PATCH", "/api/orders/456/status") == "update_order_status"

    def test_delete_removes_nested(self):
        """Test DELETE uses 'remove' for nested resources."""
        assert generate_semantic_action_name("DELETE", "/api/workspaces/123/members/456") == "remove_workspace_member"

    def test_delete_deletes_top_level(self):
        """Test DELETE uses 'delete' for top-level resources."""
        assert generate_semantic_action_name("DELETE", "/api/users/123") == "delete_user"


class TestRealWorldExamples:
    """Test real-world API path patterns."""

    def test_saas_workspace_operations(self):
        """Test SaaS workspace operations."""
        assert generate_action_name("POST", "/api/workspaces/ws_123/members") == "post_workspace_members"
        assert generate_action_name("DELETE", "/api/workspaces/ws_123/members/usr_456") == "delete_workspace_member"
        assert generate_action_name("GET", "/api/workspaces/ws_123/projects") == "get_workspace_projects"

    def test_ecommerce_operations(self):
        """Test e-commerce operations."""
        assert generate_action_name("PATCH", "/api/orders/123/status") == "patch_order_status"
        assert generate_action_name("POST", "/api/orders/123/items") == "post_order_items"
        assert generate_action_name("DELETE", "/api/orders/123/items/456") == "delete_order_item"

    def test_project_management_operations(self):
        """Test project management operations."""
        assert generate_action_name("POST", "/api/projects/proj_123/tasks") == "post_project_tasks"
        assert (
            generate_action_name("PATCH", "/api/projects/proj_123/tasks/task_456/status") == "patch_project_task_status"
        )
        assert (
            generate_action_name("POST", "/api/projects/proj_123/tasks/task_456/assignees")
            == "post_project_task_assignees"
        )
