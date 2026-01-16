// Package chi provides INEV SDK middleware for the Chi router.
package chi

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/go-chi/chi/v5"

	"github.com/Daily-Nerd/inev-sdk/go-sdk/client"
	"github.com/Daily-Nerd/inev-sdk/go-sdk/utils"
)

// contextKey is a custom type for context keys to avoid collisions.
type contextKey string

const (
	// UserIDKey is the context key for user ID.
	UserIDKey contextKey = "inev_user_id"
	// SessionIDKey is the context key for session ID.
	SessionIDKey contextKey = "inev_session_id"
)

// Config holds the configuration for the INEV middleware.
type Config struct {
	// Client is the INEV client to use for emitting events.
	Client *client.Client

	// ExcludePaths is a list of path prefixes to exclude from tracking.
	ExcludePaths []string

	// ExcludeExact is a list of exact paths to exclude from tracking.
	ExcludeExact []string

	// UseSemanticActions uses semantic action names (e.g., "create_user" instead of "post_users").
	UseSemanticActions bool

	// ExtractUserID is a function to extract the user ID from the request.
	// If nil, attempts to extract from common headers and context.
	ExtractUserID func(r *http.Request) string

	// ExtractSessionID is a function to extract the session ID from the request.
	// If nil, attempts to extract from common headers and cookies.
	ExtractSessionID func(r *http.Request) string

	// OnError is called when an error occurs during event emission.
	// If nil, errors are silently ignored to not affect request processing.
	OnError func(err error)
}

// DefaultConfig returns a Config with sensible defaults.
func DefaultConfig(c *client.Client) Config {
	return Config{
		Client: c,
		ExcludePaths: []string{
			"/health",
			"/ready",
			"/metrics",
			"/debug",
		},
		ExcludeExact: []string{
			"/",
			"/favicon.ico",
			"/robots.txt",
		},
		UseSemanticActions: true,
	}
}

// responseRecorder wraps http.ResponseWriter to capture the status code and body.
type responseRecorder struct {
	http.ResponseWriter
	statusCode int
	body       bytes.Buffer
}

func newResponseRecorder(w http.ResponseWriter) *responseRecorder {
	return &responseRecorder{
		ResponseWriter: w,
		statusCode:     http.StatusOK,
	}
}

func (r *responseRecorder) WriteHeader(code int) {
	r.statusCode = code
	r.ResponseWriter.WriteHeader(code)
}

func (r *responseRecorder) Write(b []byte) (int, error) {
	// Capture response body for error parsing (limit to 4KB)
	if r.body.Len() < 4096 {
		remaining := 4096 - r.body.Len()
		if len(b) < remaining {
			r.body.Write(b)
		} else {
			r.body.Write(b[:remaining])
		}
	}
	return r.ResponseWriter.Write(b)
}

// Middleware returns a Chi middleware that automatically tracks HTTP requests.
func Middleware(cfg Config) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			// Check if path should be excluded
			if shouldExclude(r.URL.Path, cfg.ExcludePaths, cfg.ExcludeExact) {
				next.ServeHTTP(w, r)
				return
			}

			// Wrap the response writer to capture status code and body
			rec := newResponseRecorder(w)

			// Record start time
			start := time.Now()

			// Process the request
			next.ServeHTTP(rec, r)

			// Don't track in a goroutine to avoid context issues
			go func() {
				emitEvent(r, rec, cfg, start)
			}()
		})
	}
}

// shouldExclude checks if a path should be excluded from tracking.
func shouldExclude(path string, prefixes, exact []string) bool {
	// Check exact matches
	for _, e := range exact {
		if path == e {
			return true
		}
	}

	// Check prefix matches
	for _, p := range prefixes {
		if strings.HasPrefix(path, p) {
			return true
		}
	}

	return false
}

// emitEvent creates and emits an event for the request.
func emitEvent(r *http.Request, rec *responseRecorder, cfg Config, start time.Time) {
	// Get the route pattern if available (Chi-specific)
	routePattern := chi.RouteContext(r.Context()).RoutePattern()
	path := r.URL.Path
	if routePattern != "" {
		path = routePattern
	}

	// Derive action name
	var action string
	if cfg.UseSemanticActions {
		action = utils.DeriveSemanticActionName(r.Method, path)
	} else {
		action = utils.DeriveActionName(r.Method, path)
	}

	// Extract entity and record ID
	entityInfo := utils.ExtractEntity(r.URL.Path)

	// Infer state from action and status
	transition := utils.InferFullTransition(r.Method, rec.statusCode, action)

	// Determine outcome
	var outcome client.Outcome
	switch {
	case rec.statusCode >= 200 && rec.statusCode < 300:
		outcome = client.OutcomeSuccess
	case rec.statusCode >= 400:
		outcome = client.OutcomeError
	default:
		outcome = client.OutcomePartial
	}

	// Build event options
	opts := []client.EventOption{
		client.WithEntity(entityInfo.Entity),
		client.WithRecordID(entityInfo.RecordID),
		client.WithToState(transition.ToState),
	}

	// Extract user ID
	userID := extractUserID(r, cfg.ExtractUserID)
	if userID != "" {
		opts = append(opts, client.WithUserID(userID))
	}

	// Extract session ID
	sessionID := extractSessionID(r, cfg.ExtractSessionID)
	if sessionID != "" {
		opts = append(opts, client.WithSessionID(sessionID))
	}

	// Add duration to parameters
	opts = append(opts, client.WithParameters(map[string]interface{}{
		"duration_ms":   time.Since(start).Milliseconds(),
		"method":        r.Method,
		"path":          r.URL.Path,
		"status_code":   rec.statusCode,
		"route_pattern": routePattern,
	}))

	// Parse error information for error responses
	if outcome == client.OutcomeError {
		errInfo := parseErrorResponse(rec.body.Bytes(), rec.statusCode)
		if errInfo != nil {
			opts = append(opts, client.WithError(
				errInfo.Message,
				errInfo.Code,
				errInfo.Type,
				errInfo.Category,
				errInfo.Details,
			))
		}
	}

	// Create and emit the event
	event := client.NewEvent(action, outcome, opts...)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := cfg.Client.Emit(ctx, event); err != nil {
		if cfg.OnError != nil {
			cfg.OnError(err)
		}
	}
}

// extractUserID extracts the user ID from the request.
func extractUserID(r *http.Request, custom func(*http.Request) string) string {
	// Try custom extractor first
	if custom != nil {
		if id := custom(r); id != "" {
			return id
		}
	}

	// Check context (common pattern for auth middleware)
	if id, ok := r.Context().Value(UserIDKey).(string); ok && id != "" {
		return id
	}
	if id, ok := r.Context().Value("user_id").(string); ok && id != "" {
		return id
	}
	if id, ok := r.Context().Value("userID").(string); ok && id != "" {
		return id
	}

	// Check common headers
	headers := []string{
		"X-User-ID",
		"X-User-Id",
		"X-Forwarded-User",
	}
	for _, h := range headers {
		if id := r.Header.Get(h); id != "" {
			return id
		}
	}

	return ""
}

// extractSessionID extracts the session ID from the request.
func extractSessionID(r *http.Request, custom func(*http.Request) string) string {
	// Try custom extractor first
	if custom != nil {
		if id := custom(r); id != "" {
			return id
		}
	}

	// Check context
	if id, ok := r.Context().Value(SessionIDKey).(string); ok && id != "" {
		return id
	}
	if id, ok := r.Context().Value("session_id").(string); ok && id != "" {
		return id
	}

	// Check headers
	headers := []string{
		"X-Session-ID",
		"X-Session-Id",
		"X-Request-ID",
		"X-Request-Id",
	}
	for _, h := range headers {
		if id := r.Header.Get(h); id != "" {
			return id
		}
	}

	// Check cookies
	cookies := []string{"session_id", "session", "sid"}
	for _, name := range cookies {
		if cookie, err := r.Cookie(name); err == nil && cookie.Value != "" {
			return cookie.Value
		}
	}

	return ""
}

// errorInfo holds parsed error information.
type errorInfo struct {
	Message  string
	Code     string
	Type     string
	Category client.ErrorCategory
	Details  map[string]interface{}
}

// parseErrorResponse attempts to parse error information from the response body.
func parseErrorResponse(body []byte, statusCode int) *errorInfo {
	if len(body) == 0 {
		return &errorInfo{
			Message:  http.StatusText(statusCode),
			Category: categorizeStatusCode(statusCode),
		}
	}

	var data map[string]interface{}
	if err := json.Unmarshal(body, &data); err != nil {
		return &errorInfo{
			Message:  string(body),
			Category: categorizeStatusCode(statusCode),
		}
	}

	info := &errorInfo{
		Category: categorizeStatusCode(statusCode),
		Details:  data,
	}

	// Extract message from common fields
	messageFields := []string{"message", "error", "detail", "msg"}
	for _, field := range messageFields {
		if v, ok := data[field]; ok {
			switch msg := v.(type) {
			case string:
				info.Message = msg
			case []interface{}:
				// Handle FastAPI-style validation errors
				if len(msg) > 0 {
					if first, ok := msg[0].(map[string]interface{}); ok {
						if m, ok := first["msg"].(string); ok {
							info.Message = m
						}
					}
				}
			}
			break
		}
	}

	// Extract error code
	codeFields := []string{"code", "error_code", "status"}
	for _, field := range codeFields {
		if v, ok := data[field]; ok {
			switch code := v.(type) {
			case string:
				info.Code = code
			case float64:
				info.Code = ""
			}
			break
		}
	}

	// Extract error type
	typeFields := []string{"type", "error_type"}
	for _, field := range typeFields {
		if v, ok := data[field].(string); ok {
			info.Type = v
			break
		}
	}

	return info
}

// categorizeStatusCode maps HTTP status codes to error categories.
func categorizeStatusCode(code int) client.ErrorCategory {
	switch {
	case code == 400:
		return client.ErrorCategoryValidation
	case code == 401 || code == 403:
		return client.ErrorCategoryAuth
	case code == 404:
		return client.ErrorCategoryNotFound
	case code == 429:
		return client.ErrorCategoryRateLimit
	case code >= 500:
		return client.ErrorCategoryServer
	default:
		return client.ErrorCategoryValidation
	}
}

// SetUserID sets the user ID in the request context.
func SetUserID(ctx context.Context, userID string) context.Context {
	return context.WithValue(ctx, UserIDKey, userID)
}

// SetSessionID sets the session ID in the request context.
func SetSessionID(ctx context.Context, sessionID string) context.Context {
	return context.WithValue(ctx, SessionIDKey, sessionID)
}

// Deprecated: unused but kept for future use
var _ = io.Discard
