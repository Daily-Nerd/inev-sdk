package utils

import (
	"testing"
)

func TestDeriveActionName(t *testing.T) {
	tests := []struct {
		method   string
		path     string
		expected string
	}{
		// Basic CRUD operations
		{"GET", "/api/users", "get_users"},
		{"POST", "/api/users", "post_users"},
		{"GET", "/api/users/123", "get_user"},
		{"PUT", "/api/users/123", "put_user"},
		{"PATCH", "/api/users/123", "patch_user"},
		{"DELETE", "/api/users/123", "delete_user"},

		// Nested resources
		{"GET", "/api/workspaces/ws_123/members", "get_workspace_members"},
		{"POST", "/api/workspaces/ws_123/members", "post_workspace_members"},
		{"DELETE", "/api/projects/proj_456/members/usr_789", "delete_project_member"},

		// With version prefix
		{"GET", "/api/v1/orders", "get_orders"},
		{"POST", "/api/v2/orders", "post_orders"},
		{"GET", "/api/v1/orders/12345", "get_order"},

		// UUIDs as IDs
		{"GET", "/api/orders/550e8400-e29b-41d4-a716-446655440000", "get_order"},

		// Path placeholders
		{"GET", "/api/users/{user_id}/posts", "get_user_posts"},
		{"GET", "/api/users/{user_id}/posts/{post_id}", "get_user_post"},

		// Edge cases
		{"GET", "/", "get"},
		{"GET", "/api", "get"},
		{"GET", "/health", "get_health"},
	}

	for _, tt := range tests {
		t.Run(tt.method+"_"+tt.path, func(t *testing.T) {
			result := DeriveActionName(tt.method, tt.path)
			if result != tt.expected {
				t.Errorf("DeriveActionName(%q, %q) = %q, want %q",
					tt.method, tt.path, result, tt.expected)
			}
		})
	}
}

func TestDeriveSemanticActionName(t *testing.T) {
	tests := []struct {
		method   string
		path     string
		expected string
	}{
		// Basic CRUD with semantic verbs
		{"GET", "/api/users", "list_users"},
		{"GET", "/api/users/123", "get_user"},
		{"POST", "/api/users", "create_user"},
		{"PUT", "/api/users/123", "update_user"},
		{"PATCH", "/api/users/123", "update_user"},
		{"DELETE", "/api/users/123", "delete_user"},

		// Nested resources
		{"GET", "/api/workspaces/ws_123/members", "list_members"},
		{"POST", "/api/workspaces/ws_123/members", "create_member"},
		{"DELETE", "/api/projects/proj_456/members/usr_789", "delete_member"},

		// Edge cases
		{"GET", "/", "get"},
		{"GET", "/api", "get"},
	}

	for _, tt := range tests {
		t.Run(tt.method+"_"+tt.path, func(t *testing.T) {
			result := DeriveSemanticActionName(tt.method, tt.path)
			if result != tt.expected {
				t.Errorf("DeriveSemanticActionName(%q, %q) = %q, want %q",
					tt.method, tt.path, result, tt.expected)
			}
		})
	}
}

func TestIsIDSegment(t *testing.T) {
	tests := []struct {
		segment  string
		expected bool
	}{
		// UUIDs
		{"550e8400-e29b-41d4-a716-446655440000", true},
		{"123e4567-e89b-12d3-a456-426614174000", true},

		// Numeric IDs
		{"123", true},
		{"1", true},
		{"999999", true},

		// Prefixed IDs
		{"ws_123", true},
		{"proj_abc", true},
		{"user_xyz123", true},

		// Placeholders
		{"{id}", true},
		{"{user_id}", true},

		// Non-IDs
		{"users", false},
		{"orders", false},
		{"api", false},
		{"v1", false},
	}

	for _, tt := range tests {
		t.Run(tt.segment, func(t *testing.T) {
			result := isIDSegment(tt.segment)
			if result != tt.expected {
				t.Errorf("isIDSegment(%q) = %v, want %v",
					tt.segment, result, tt.expected)
			}
		})
	}
}

func TestSingularize(t *testing.T) {
	tests := []struct {
		word     string
		expected string
	}{
		// Regular plurals
		{"users", "user"},
		{"orders", "order"},
		{"products", "product"},

		// -ies plurals
		{"categories", "category"},
		{"policies", "policy"},

		// -es plurals
		{"boxes", "box"},
		{"matches", "match"},
		{"buses", "bus"},

		// Irregular plurals
		{"people", "person"},
		{"children", "child"},
		{"statuses", "status"},

		// Already singular
		{"user", "user"},
		{"order", "order"},
	}

	for _, tt := range tests {
		t.Run(tt.word, func(t *testing.T) {
			result := singularize(tt.word)
			if result != tt.expected {
				t.Errorf("singularize(%q) = %q, want %q",
					tt.word, result, tt.expected)
			}
		})
	}
}
