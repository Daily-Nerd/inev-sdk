"""Tests for HTTP state inference."""

from inev_sdk.utils.state_inference import (
    infer_from_state_from_method,
    infer_state_from_http,
)


class TestInferStateFromHttp:
    """Tests for infer_state_from_http function."""

    # POST tests
    def test_post_201_created(self):
        """Test POST with 201 Created."""
        assert infer_state_from_http("POST", 201) == "created"

    def test_post_200_processed(self):
        """Test POST with 200 OK (non-creation)."""
        assert infer_state_from_http("POST", 200) == "processed"

    def test_post_202_pending(self):
        """Test POST with 202 Accepted (async)."""
        assert infer_state_from_http("POST", 202) == "pending"

    def test_post_with_action_confirm(self):
        """Test POST with confirm action hint."""
        assert infer_state_from_http("POST", 200, "post_order_confirm") == "confirmed"

    def test_post_with_action_submit(self):
        """Test POST with submit action hint."""
        assert infer_state_from_http("POST", 200, "post_form_submit") == "submitted"

    # PUT tests
    def test_put_200_updated(self):
        """Test PUT with 200 OK."""
        assert infer_state_from_http("PUT", 200) == "updated"

    def test_put_204_updated(self):
        """Test PUT with 204 No Content."""
        assert infer_state_from_http("PUT", 204) == "updated"

    def test_put_201_created(self):
        """Test PUT with 201 Created (upsert)."""
        assert infer_state_from_http("PUT", 201) == "created"

    # PATCH tests
    def test_patch_200_updated(self):
        """Test PATCH with 200 OK."""
        assert infer_state_from_http("PATCH", 200) == "updated"

    def test_patch_204_updated(self):
        """Test PATCH with 204 No Content."""
        assert infer_state_from_http("PATCH", 204) == "updated"

    def test_patch_with_action_activate(self):
        """Test PATCH with activate action hint."""
        assert infer_state_from_http("PATCH", 200, "patch_user_activate") == "activated"

    def test_patch_with_action_suspend(self):
        """Test PATCH with suspend action hint."""
        assert infer_state_from_http("PATCH", 200, "patch_account_suspend") == "suspended"

    # DELETE tests
    def test_delete_200_deleted(self):
        """Test DELETE with 200 OK."""
        assert infer_state_from_http("DELETE", 200) == "deleted"

    def test_delete_204_deleted(self):
        """Test DELETE with 204 No Content."""
        assert infer_state_from_http("DELETE", 204) == "deleted"

    def test_delete_202_deleting(self):
        """Test DELETE with 202 Accepted (async deletion)."""
        assert infer_state_from_http("DELETE", 202) == "deleting"

    # GET tests (no state change)
    def test_get_200_none(self):
        """Test GET returns None (no state change)."""
        assert infer_state_from_http("GET", 200) is None

    def test_get_404_none(self):
        """Test GET 404 returns None."""
        assert infer_state_from_http("GET", 404) is None

    # Error responses
    def test_post_400_none(self):
        """Test POST 400 returns None (error)."""
        assert infer_state_from_http("POST", 400) is None

    def test_post_500_none(self):
        """Test POST 500 returns None (error)."""
        assert infer_state_from_http("POST", 500) is None

    def test_delete_403_none(self):
        """Test DELETE 403 returns None (forbidden)."""
        assert infer_state_from_http("DELETE", 403) is None

    # Redirect responses
    def test_post_301_none(self):
        """Test POST 301 returns None (redirect)."""
        assert infer_state_from_http("POST", 301) is None

    def test_post_302_none(self):
        """Test POST 302 returns None (redirect)."""
        assert infer_state_from_http("POST", 302) is None

    # HEAD/OPTIONS (no state change)
    def test_head_200_none(self):
        """Test HEAD returns None."""
        assert infer_state_from_http("HEAD", 200) is None

    def test_options_200_none(self):
        """Test OPTIONS returns None."""
        assert infer_state_from_http("OPTIONS", 200) is None

    # Case insensitivity
    def test_lowercase_method(self):
        """Test lowercase method works."""
        assert infer_state_from_http("post", 201) == "created"

    def test_mixed_case_method(self):
        """Test mixed case method works."""
        assert infer_state_from_http("Post", 201) == "created"


class TestInferFromStateFromMethod:
    """Tests for infer_from_state_from_method function."""

    def test_delete_implies_active(self):
        """Test DELETE implies 'active' from_state."""
        assert infer_from_state_from_method("DELETE") == "active"

    def test_post_none(self):
        """Test POST cannot infer from_state."""
        assert infer_from_state_from_method("POST") is None

    def test_put_none(self):
        """Test PUT cannot infer from_state."""
        assert infer_from_state_from_method("PUT") is None

    def test_get_none(self):
        """Test GET cannot infer from_state."""
        assert infer_from_state_from_method("GET") is None

    def test_lowercase_method(self):
        """Test lowercase method works."""
        assert infer_from_state_from_method("delete") == "active"


class TestActionBasedStateInference:
    """Tests for action-based state inference."""

    def test_approve_action(self):
        """Test approve action inference."""
        assert infer_state_from_http("POST", 200, "approve_request") == "approved"

    def test_reject_action(self):
        """Test reject action inference."""
        assert infer_state_from_http("POST", 200, "reject_application") == "rejected"

    def test_cancel_action(self):
        """Test cancel action inference."""
        assert infer_state_from_http("POST", 200, "cancel_order") == "cancelled"

    def test_archive_action(self):
        """Test archive action inference."""
        assert infer_state_from_http("POST", 200, "archive_project") == "archived"

    def test_ship_action(self):
        """Test ship action inference."""
        assert infer_state_from_http("POST", 200, "ship_order") == "shipped"

    def test_deliver_action(self):
        """Test deliver action inference."""
        assert infer_state_from_http("POST", 200, "deliver_package") == "delivered"

    def test_refund_action(self):
        """Test refund action inference."""
        assert infer_state_from_http("POST", 200, "refund_payment") == "refunded"

    def test_complete_action(self):
        """Test complete action inference."""
        assert infer_state_from_http("POST", 200, "complete_task") == "completed"

    def test_publish_action(self):
        """Test publish action inference."""
        assert infer_state_from_http("PATCH", 200, "patch_article_publish") == "published"

    def test_enable_action(self):
        """Test enable action inference."""
        assert infer_state_from_http("PATCH", 200, "enable_feature") == "enabled"

    def test_disable_action(self):
        """Test disable action inference."""
        assert infer_state_from_http("PATCH", 200, "disable_feature") == "disabled"
