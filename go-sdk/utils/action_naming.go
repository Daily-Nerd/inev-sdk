// Package utils provides utility functions for the INEV SDK.
package utils

import (
	"regexp"
	"strings"
)

var (
	// uuidPattern matches UUIDs
	uuidPattern = regexp.MustCompile(`^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`)

	// numericPattern matches purely numeric IDs
	numericPattern = regexp.MustCompile(`^\d+$`)

	// prefixedIDPattern matches prefixed IDs like ws_123, proj_abc
	prefixedIDPattern = regexp.MustCompile(`^[a-z]{1,10}_[a-z0-9]+$`)

	// placeholderPattern matches path placeholders like {id}, {user_id}
	placeholderPattern = regexp.MustCompile(`^\{[a-zA-Z_]+\}$`)

	// versionPattern matches API version segments like v1, v2
	versionPattern = regexp.MustCompile(`^v\d+$`)

	// Irregular plurals
	irregularPlurals = map[string]string{
		"people":   "person",
		"children": "child",
		"men":      "man",
		"women":    "woman",
		"mice":     "mouse",
		"geese":    "goose",
		"teeth":    "tooth",
		"feet":     "foot",
		"data":     "datum",
		"criteria": "criterion",
		"analyses": "analysis",
		"statuses": "status",
	}
)

// DeriveActionName derives a semantic action name from an HTTP method and path.
// Example: POST /api/workspaces/{id}/members → post_workspace_members
func DeriveActionName(method, path string) string {
	segments := cleanPath(path)
	if len(segments) == 0 {
		return strings.ToLower(method)
	}

	var parts []string
	parts = append(parts, strings.ToLower(method))

	for i, segment := range segments {
		if isIDSegment(segment) {
			continue
		}

		// Singularize if followed by an ID segment
		name := segment
		if i+1 < len(segments) && isIDSegment(segments[i+1]) {
			name = singularize(segment)
		}

		parts = append(parts, name)
	}

	return strings.Join(parts, "_")
}

// DeriveSemanticActionName derives a more semantic action name using verb mapping.
// Example: GET /api/users → list_users, POST /api/orders → create_order
func DeriveSemanticActionName(method, path string) string {
	segments := cleanPath(path)
	if len(segments) == 0 {
		return strings.ToLower(method)
	}

	// Find the last non-ID segment (the main resource)
	var resource string
	var hasTrailingID bool
	for i := len(segments) - 1; i >= 0; i-- {
		if !isIDSegment(segments[i]) {
			resource = segments[i]
			hasTrailingID = i < len(segments)-1
			break
		}
	}

	if resource == "" {
		return strings.ToLower(method)
	}

	verb := mapMethodToVerb(method, resource, hasTrailingID)

	// For list operations, keep plural; for single operations, singularize
	if verb == "list" {
		return verb + "_" + resource
	}
	return verb + "_" + singularize(resource)
}

// cleanPath removes /api prefix, version segments, and splits path into segments.
func cleanPath(path string) []string {
	// Remove leading slash
	path = strings.TrimPrefix(path, "/")

	// Split into segments
	parts := strings.Split(path, "/")

	var segments []string
	for _, part := range parts {
		part = strings.TrimSpace(part)
		if part == "" {
			continue
		}
		// Skip 'api' prefix
		if part == "api" {
			continue
		}
		// Skip version segments
		if versionPattern.MatchString(part) {
			continue
		}
		segments = append(segments, strings.ToLower(part))
	}

	return segments
}

// isIDSegment checks if a path segment represents an ID.
func isIDSegment(segment string) bool {
	segment = strings.ToLower(segment)

	// Check UUID
	if uuidPattern.MatchString(segment) {
		return true
	}

	// Check numeric ID
	if numericPattern.MatchString(segment) {
		return true
	}

	// Check prefixed ID
	if prefixedIDPattern.MatchString(segment) {
		return true
	}

	// Check placeholder
	if placeholderPattern.MatchString(segment) {
		return true
	}

	return false
}

// singularize converts a plural word to singular.
func singularize(word string) string {
	word = strings.ToLower(word)

	// Check irregular plurals
	if singular, ok := irregularPlurals[word]; ok {
		return singular
	}

	// Common patterns
	switch {
	case strings.HasSuffix(word, "ies"):
		return word[:len(word)-3] + "y"
	case strings.HasSuffix(word, "ves"):
		return word[:len(word)-3] + "f"
	case strings.HasSuffix(word, "oes") && len(word) > 3:
		return word[:len(word)-2]
	case strings.HasSuffix(word, "ses") || strings.HasSuffix(word, "xes") ||
		strings.HasSuffix(word, "ches") || strings.HasSuffix(word, "shes"):
		return word[:len(word)-2]
	case strings.HasSuffix(word, "s") && !strings.HasSuffix(word, "ss"):
		return word[:len(word)-1]
	}

	return word
}

// mapMethodToVerb maps HTTP method to a semantic verb.
func mapMethodToVerb(method, _ string, hasTrailingID bool) string {
	method = strings.ToUpper(method)

	switch method {
	case "GET":
		if hasTrailingID {
			return "get"
		}
		return "list"
	case "POST":
		return "create"
	case "PUT":
		return "update"
	case "PATCH":
		return "update"
	case "DELETE":
		return "delete"
	default:
		return strings.ToLower(method)
	}
}
