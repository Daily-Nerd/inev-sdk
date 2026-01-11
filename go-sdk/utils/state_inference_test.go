package utils

import (
	"testing"
)

func TestInferState(t *testing.T) {
	tests := []struct {
		method     string
		statusCode int
		expected   string
	}{
		// POST
		{"POST", 201, "created"},
		{"POST", 200, "processed"},
		{"POST", 202, "processed"},
		{"POST", 400, ""},
		{"POST", 500, ""},

		// PUT
		{"PUT", 200, "updated"},
		{"PUT", 204, "updated"},
		{"PUT", 400, ""},

		// PATCH
		{"PATCH", 200, "updated"},
		{"PATCH", 204, "updated"},
		{"PATCH", 400, ""},

		// DELETE
		{"DELETE", 200, "deleted"},
		{"DELETE", 204, "deleted"},
		{"DELETE", 202, "deleted"},
		{"DELETE", 404, ""},

		// GET (no state change)
		{"GET", 200, ""},
		{"GET", 404, ""},
	}

	for _, tt := range tests {
		t.Run(tt.method+"_"+string(rune(tt.statusCode)), func(t *testing.T) {
			result := InferState(tt.method, tt.statusCode)
			if result != tt.expected {
				t.Errorf("InferState(%q, %d) = %q, want %q",
					tt.method, tt.statusCode, result, tt.expected)
			}
		})
	}
}

func TestInferStateFromAction(t *testing.T) {
	tests := []struct {
		action   string
		expected string
	}{
		// Lifecycle
		{"create_user", "created"},
		{"update_order", "updated"},
		{"delete_product", "deleted"},

		// Approval workflow
		{"confirm_order", "confirmed"},
		{"approve_request", "approved"},
		{"reject_application", "rejected"},
		{"cancel_subscription", "cancelled"},

		// Activation
		{"activate_account", "activated"},
		{"deactivate_user", "deactivated"},
		{"suspend_membership", "suspended"},
		{"resume_service", "resumed"},

		// Progress
		{"start_job", "started"},
		{"stop_process", "stopped"},
		{"complete_task", "completed"},
		{"submit_form", "submitted"},

		// Publishing
		{"publish_article", "published"},
		{"unpublish_post", "unpublished"},

		// E-commerce
		{"ship_order", "shipped"},
		{"deliver_package", "delivered"},
		{"refund_payment", "refunded"},

		// No matching verb
		{"get_user", ""},
		{"list_orders", ""},
	}

	for _, tt := range tests {
		t.Run(tt.action, func(t *testing.T) {
			result := InferStateFromAction(tt.action)
			if result != tt.expected {
				t.Errorf("InferStateFromAction(%q) = %q, want %q",
					tt.action, result, tt.expected)
			}
		})
	}
}

func TestInferFullTransition(t *testing.T) {
	tests := []struct {
		method     string
		statusCode int
		action     string
		expected   StateTransition
	}{
		// Action takes precedence
		{"POST", 201, "confirm_order", StateTransition{ToState: "confirmed"}},
		{"POST", 200, "approve_request", StateTransition{ToState: "approved"}},

		// Fall back to HTTP method + status
		{"POST", 201, "post_users", StateTransition{ToState: "created"}},
		{"PUT", 200, "put_order", StateTransition{ToState: "updated"}},
		{"DELETE", 204, "delete_product", StateTransition{ToState: "deleted"}},

		// Action-based inference takes precedence (tracks intended action)
		{"POST", 400, "create_user", StateTransition{ToState: "created"}},
		{"DELETE", 404, "delete_nonexistent", StateTransition{ToState: "deleted"}},

		// No state verb in action, no state for errors
		{"DELETE", 404, "remove_item", StateTransition{ToState: "removed"}},
		{"GET", 404, "get_user", StateTransition{ToState: ""}},
	}

	for _, tt := range tests {
		t.Run(tt.action, func(t *testing.T) {
			result := InferFullTransition(tt.method, tt.statusCode, tt.action)
			if result.ToState != tt.expected.ToState {
				t.Errorf("InferFullTransition(%q, %d, %q) = %+v, want %+v",
					tt.method, tt.statusCode, tt.action, result, tt.expected)
			}
		})
	}
}

func TestStatusHelpers(t *testing.T) {
	tests := []struct {
		code         int
		isSuccess    bool
		isClientErr  bool
		isServerErr  bool
	}{
		{200, true, false, false},
		{201, true, false, false},
		{204, true, false, false},
		{301, false, false, false},
		{400, false, true, false},
		{401, false, true, false},
		{404, false, true, false},
		{500, false, false, true},
		{502, false, false, true},
	}

	for _, tt := range tests {
		t.Run(string(rune(tt.code)), func(t *testing.T) {
			if IsSuccessStatus(tt.code) != tt.isSuccess {
				t.Errorf("IsSuccessStatus(%d) = %v, want %v",
					tt.code, IsSuccessStatus(tt.code), tt.isSuccess)
			}
			if IsClientError(tt.code) != tt.isClientErr {
				t.Errorf("IsClientError(%d) = %v, want %v",
					tt.code, IsClientError(tt.code), tt.isClientErr)
			}
			if IsServerError(tt.code) != tt.isServerErr {
				t.Errorf("IsServerError(%d) = %v, want %v",
					tt.code, IsServerError(tt.code), tt.isServerErr)
			}
		})
	}
}
