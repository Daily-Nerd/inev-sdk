package utils

import (
	"strings"
)

// StateTransition represents a from/to state pair.
type StateTransition struct {
	FromState string
	ToState   string
}

// InferState infers the state transition based on HTTP method and status code.
// Returns the to_state (from_state is typically not inferable without prior context).
func InferState(method string, statusCode int) string {
	method = strings.ToUpper(method)

	// Error status codes don't result in state changes
	if statusCode >= 400 {
		return ""
	}

	switch method {
	case "POST":
		switch statusCode {
		case 201:
			return "created"
		case 200, 202:
			return "processed"
		default:
			return ""
		}
	case "PUT":
		if statusCode == 200 || statusCode == 204 {
			return "updated"
		}
	case "PATCH":
		if statusCode == 200 || statusCode == 204 {
			return "updated"
		}
	case "DELETE":
		if statusCode == 200 || statusCode == 204 || statusCode == 202 {
			return "deleted"
		}
	case "GET":
		// GET requests don't change state
		return ""
	}

	return ""
}

// InferStateFromAction infers state from the action name.
// This handles cases where the action verb indicates the target state.
func InferStateFromAction(action string) string {
	action = strings.ToLower(action)

	// Extract the verb from action names like "confirm_order", "post_order_confirm"
	parts := strings.Split(action, "_")

	// Check each part for a state-indicating verb
	stateVerbs := map[string]string{
		// Lifecycle states
		"create":    "created",
		"created":   "created",
		"update":    "updated",
		"updated":   "updated",
		"delete":    "deleted",
		"deleted":   "deleted",
		"remove":    "removed",
		"removed":   "removed",
		"archive":   "archived",
		"archived":  "archived",
		"unarchive": "unarchived",
		"restore":   "restored",

		// Approval workflow
		"confirm":   "confirmed",
		"confirmed": "confirmed",
		"approve":   "approved",
		"approved":  "approved",
		"reject":    "rejected",
		"rejected":  "rejected",
		"cancel":    "canceled",
		"canceled":  "canceled",

		// Activation states
		"activate":   "activated",
		"activated":  "activated",
		"deactivate": "deactivated",
		"suspend":    "suspended",
		"suspended":  "suspended",
		"resume":     "resumed",
		"resumed":    "resumed",
		"enable":     "enabled",
		"enabled":    "enabled",
		"disable":    "disabled",
		"disabled":   "disabled",

		// Progress states
		"start":     "started",
		"started":   "started",
		"stop":      "stopped",
		"stopped":   "stopped",
		"pause":     "paused",
		"paused":    "paused",
		"complete":  "completed",
		"completed": "completed",
		"finish":    "finished",
		"finished":  "finished",

		// Submission states
		"submit":    "submitted",
		"submitted": "submitted",
		"publish":   "published",
		"published": "published",
		"unpublish": "unpublished",
		"draft":     "draft",

		// Verification states
		"verify":     "verified",
		"verified":   "verified",
		"validate":   "validated",
		"invalidate": "invalidated",

		// E-commerce states
		"ship":      "shipped",
		"shipped":   "shipped",
		"deliver":   "delivered",
		"delivered": "delivered",
		"refund":    "refunded",
		"refunded":  "refunded",
		"pay":       "paid",
		"paid":      "paid",

		// Expiration states
		"expire":   "expired",
		"expired":  "expired",
		"renew":    "renewed",
		"renewed":  "renewed",
		"extend":   "extended",
		"extended": "extended",

		// Upgrade states
		"upgrade":    "upgraded",
		"upgraded":   "upgraded",
		"downgrade":  "downgraded",
		"downgraded": "downgraded",

		// Assignment states
		"assign":   "assigned",
		"assigned": "assigned",
		"unassign": "unassigned",
		"transfer": "transferred",

		// Lock states
		"lock":     "locked",
		"locked":   "locked",
		"unlock":   "unlocked",
		"unlocked": "unlocked",
	}

	for _, part := range parts {
		if state, ok := stateVerbs[part]; ok {
			return state
		}
	}

	return ""
}

// InferFullTransition attempts to infer both from and to states.
// This is most useful when the action contains the state verb.
func InferFullTransition(method string, statusCode int, action string) StateTransition {
	trans := StateTransition{}

	// Try to infer to_state from action first
	if action != "" {
		trans.ToState = InferStateFromAction(action)
	}

	// Fall back to HTTP method + status code
	if trans.ToState == "" {
		trans.ToState = InferState(method, statusCode)
	}

	return trans
}

// IsSuccessStatus returns true if the status code indicates success.
func IsSuccessStatus(statusCode int) bool {
	return statusCode >= 200 && statusCode < 300
}

// IsClientError returns true if the status code indicates a client error.
func IsClientError(statusCode int) bool {
	return statusCode >= 400 && statusCode < 500
}

// IsServerError returns true if the status code indicates a server error.
func IsServerError(statusCode int) bool {
	return statusCode >= 500
}
