// Package client provides the core INEV SDK client for event emission.
package client

import (
	"time"

	"github.com/google/uuid"
)

// Outcome represents the result of an action.
type Outcome string

const (
	OutcomeSuccess Outcome = "success"
	OutcomeError   Outcome = "error"
	OutcomePartial Outcome = "partial"
)

// ErrorCategory represents the category of an error.
type ErrorCategory string

const (
	ErrorCategoryValidation ErrorCategory = "validation"
	ErrorCategoryAuth       ErrorCategory = "auth"
	ErrorCategoryNotFound   ErrorCategory = "not_found"
	ErrorCategoryNetwork    ErrorCategory = "network"
	ErrorCategoryRateLimit  ErrorCategory = "rate_limit"
	ErrorCategoryServer     ErrorCategory = "server"
)

// Event represents an INEV event to be emitted.
type Event struct {
	EventID       string                 `json:"event_id"`
	Timestamp     string                 `json:"timestamp"`
	Entity        string                 `json:"entity,omitempty"`
	Action        string                 `json:"action"`
	RecordID      string                 `json:"record_id,omitempty"`
	FromState     string                 `json:"from_state,omitempty"`
	ToState       string                 `json:"to_state,omitempty"`
	Outcome       Outcome                `json:"outcome"`
	ErrorMessage  string                 `json:"error_message,omitempty"`
	ErrorCode     string                 `json:"error_code,omitempty"`
	ErrorType     string                 `json:"error_type,omitempty"`
	ErrorCategory ErrorCategory          `json:"error_category,omitempty"`
	ErrorDetails  map[string]interface{} `json:"error_details,omitempty"`
	UserID        string                 `json:"user_id,omitempty"`
	SessionID     string                 `json:"session_id,omitempty"`
	Parameters    map[string]interface{} `json:"parameters,omitempty"`
	Environment   string                 `json:"environment"`
	Source        string                 `json:"source"`
	Extra         map[string]interface{} `json:"-"` // Additional fields merged at JSON level
}

// EventOption is a functional option for configuring an Event.
type EventOption func(*Event)

// NewEvent creates a new Event with the given action and options.
func NewEvent(action string, outcome Outcome, opts ...EventOption) *Event {
	e := &Event{
		EventID:     uuid.New().String(),
		Timestamp:   time.Now().UTC().Format(time.RFC3339Nano),
		Action:      action,
		Outcome:     outcome,
		Environment: "production",
		Source:      "inev-go-sdk",
		Parameters:  make(map[string]interface{}),
		Extra:       make(map[string]interface{}),
	}

	for _, opt := range opts {
		opt(e)
	}

	return e
}

// WithEntity sets the entity for the event.
func WithEntity(entity string) EventOption {
	return func(e *Event) {
		e.Entity = entity
	}
}

// WithRecordID sets the record ID for the event.
func WithRecordID(recordID string) EventOption {
	return func(e *Event) {
		e.RecordID = recordID
	}
}

// WithFromState sets the from_state for the event.
func WithFromState(state string) EventOption {
	return func(e *Event) {
		e.FromState = state
	}
}

// WithToState sets the to_state for the event.
func WithToState(state string) EventOption {
	return func(e *Event) {
		e.ToState = state
	}
}

// WithError sets error information for the event.
func WithError(message, code, errType string, category ErrorCategory, details map[string]interface{}) EventOption {
	return func(e *Event) {
		e.ErrorMessage = message
		e.ErrorCode = code
		e.ErrorType = errType
		e.ErrorCategory = category
		e.ErrorDetails = details
	}
}

// WithUserID sets the user ID for the event.
func WithUserID(userID string) EventOption {
	return func(e *Event) {
		e.UserID = userID
	}
}

// WithSessionID sets the session ID for the event.
func WithSessionID(sessionID string) EventOption {
	return func(e *Event) {
		e.SessionID = sessionID
	}
}

// WithParameters sets the parameters for the event.
func WithParameters(params map[string]interface{}) EventOption {
	return func(e *Event) {
		e.Parameters = params
	}
}

// EventWithEnvironment sets the environment for the event.
func EventWithEnvironment(env string) EventOption {
	return func(e *Event) {
		e.Environment = env
	}
}

// EventWithSource sets the source for the event.
func EventWithSource(source string) EventOption {
	return func(e *Event) {
		e.Source = source
	}
}

// WithExtra sets additional fields for the event.
func WithExtra(key string, value interface{}) EventOption {
	return func(e *Event) {
		if e.Extra == nil {
			e.Extra = make(map[string]interface{})
		}
		e.Extra[key] = value
	}
}
