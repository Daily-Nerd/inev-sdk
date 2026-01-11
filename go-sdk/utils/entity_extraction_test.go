package utils

import (
	"testing"
)

func TestExtractEntity(t *testing.T) {
	tests := []struct {
		path     string
		expected EntityInfo
	}{
		// Simple paths
		{"/api/users", EntityInfo{Entity: "user", RecordID: ""}},
		{"/api/users/123", EntityInfo{Entity: "user", RecordID: "123"}},
		{"/api/v1/orders/456", EntityInfo{Entity: "order", RecordID: "456"}},

		// Nested paths - should return the last entity
		{"/api/workspaces/ws_123/members", EntityInfo{Entity: "member", RecordID: ""}},
		{"/api/workspaces/ws_123/members/usr_456", EntityInfo{Entity: "member", RecordID: "usr_456"}},
		{"/api/users/123/posts/456/comments", EntityInfo{Entity: "comment", RecordID: ""}},
		{"/api/users/123/posts/456/comments/789", EntityInfo{Entity: "comment", RecordID: "789"}},

		// UUIDs
		{"/api/orders/550e8400-e29b-41d4-a716-446655440000", EntityInfo{Entity: "order", RecordID: "550e8400-e29b-41d4-a716-446655440000"}},

		// Edge cases
		{"/", EntityInfo{}},
		{"/api", EntityInfo{}},
		{"/health", EntityInfo{Entity: "health", RecordID: ""}},
	}

	for _, tt := range tests {
		t.Run(tt.path, func(t *testing.T) {
			result := ExtractEntity(tt.path)
			if result.Entity != tt.expected.Entity || result.RecordID != tt.expected.RecordID {
				t.Errorf("ExtractEntity(%q) = %+v, want %+v",
					tt.path, result, tt.expected)
			}
		})
	}
}

func TestExtractParentEntity(t *testing.T) {
	tests := []struct {
		path     string
		expected EntityInfo
	}{
		// Nested paths - should return the parent entity
		{"/api/workspaces/ws_123/members", EntityInfo{Entity: "workspace", RecordID: "ws_123"}},
		{"/api/workspaces/ws_123/members/usr_456", EntityInfo{Entity: "workspace", RecordID: "ws_123"}},
		{"/api/users/123/posts/456", EntityInfo{Entity: "user", RecordID: "123"}},

		// Not enough segments
		{"/api/users", EntityInfo{}},
		{"/api/users/123", EntityInfo{}},
		{"/", EntityInfo{}},
	}

	for _, tt := range tests {
		t.Run(tt.path, func(t *testing.T) {
			result := ExtractParentEntity(tt.path)
			if result.Entity != tt.expected.Entity || result.RecordID != tt.expected.RecordID {
				t.Errorf("ExtractParentEntity(%q) = %+v, want %+v",
					tt.path, result, tt.expected)
			}
		})
	}
}

func TestExtractAllEntities(t *testing.T) {
	tests := []struct {
		path     string
		expected []EntityInfo
	}{
		{
			"/api/workspaces/ws_123/projects/proj_456/members",
			[]EntityInfo{
				{Entity: "workspace", RecordID: "ws_123"},
				{Entity: "project", RecordID: "proj_456"},
				{Entity: "member", RecordID: ""},
			},
		},
		{
			"/api/users/123/posts/456",
			[]EntityInfo{
				{Entity: "user", RecordID: "123"},
				{Entity: "post", RecordID: "456"},
			},
		},
		{
			"/api/orders",
			[]EntityInfo{
				{Entity: "order", RecordID: ""},
			},
		},
		{
			"/",
			nil,
		},
	}

	for _, tt := range tests {
		t.Run(tt.path, func(t *testing.T) {
			result := ExtractAllEntities(tt.path)
			if len(result) != len(tt.expected) {
				t.Errorf("ExtractAllEntities(%q) returned %d entities, want %d",
					tt.path, len(result), len(tt.expected))
				return
			}
			for i, e := range tt.expected {
				if result[i].Entity != e.Entity || result[i].RecordID != e.RecordID {
					t.Errorf("ExtractAllEntities(%q)[%d] = %+v, want %+v",
						tt.path, i, result[i], e)
				}
			}
		})
	}
}

func TestNormalizeEntityName(t *testing.T) {
	tests := []struct {
		name     string
		expected string
	}{
		{"users", "user"},
		{"User", "user"},
		{"user-profiles", "user_profile"},
		{"order items", "order_item"},
		{"PRODUCTS", "product"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := NormalizeEntityName(tt.name)
			if result != tt.expected {
				t.Errorf("NormalizeEntityName(%q) = %q, want %q",
					tt.name, result, tt.expected)
			}
		})
	}
}
