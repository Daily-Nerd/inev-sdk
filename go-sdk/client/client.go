package client

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"sync"
	"time"
)

// Config holds the configuration for the INEV client.
type Config struct {
	// APIKey is the API key for authenticating with the INEV backend.
	APIKey string

	// Endpoint is the URL of the INEV backend.
	Endpoint string

	// Environment is the environment name (e.g., "production", "staging").
	Environment string

	// BatchSize is the maximum number of events to batch before flushing.
	BatchSize int

	// FlushInterval is the interval at which to flush events.
	FlushInterval time.Duration

	// HTTPClient is an optional custom HTTP client.
	HTTPClient *http.Client

	// Source identifies the SDK source.
	Source string
}

// DefaultConfig returns a Config with sensible defaults.
func DefaultConfig() Config {
	return Config{
		Endpoint:      "https://api.inev.io/v1/events",
		Environment:   "production",
		BatchSize:     100,
		FlushInterval: 5 * time.Second,
		Source:        "inev-go-sdk",
	}
}

// Client is the INEV SDK client for emitting events.
type Client struct {
	config Config

	mu      sync.Mutex
	batch   []*Event
	closed  bool
	closeCh chan struct{}
	flushWg sync.WaitGroup
	httpCli *http.Client
}

// New creates a new INEV client with the given API key and options.
func New(apiKey string, opts ...Option) *Client {
	cfg := DefaultConfig()
	cfg.APIKey = apiKey

	for _, opt := range opts {
		opt(&cfg)
	}

	httpCli := cfg.HTTPClient
	if httpCli == nil {
		httpCli = &http.Client{
			Timeout: 30 * time.Second,
		}
	}

	c := &Client{
		config:  cfg,
		batch:   make([]*Event, 0, cfg.BatchSize),
		closeCh: make(chan struct{}),
		httpCli: httpCli,
	}

	// Start background flush goroutine
	c.flushWg.Add(1)
	go c.backgroundFlush()

	return c
}

// Option is a functional option for configuring the Client.
type Option func(*Config)

// WithEndpoint sets a custom endpoint.
func WithEndpoint(endpoint string) Option {
	return func(c *Config) {
		c.Endpoint = endpoint
	}
}

// WithEnvironment sets the environment.
func WithEnvironment(env string) Option {
	return func(c *Config) {
		c.Environment = env
	}
}

// WithBatchSize sets the batch size.
func WithBatchSize(size int) Option {
	return func(c *Config) {
		c.BatchSize = size
	}
}

// WithFlushInterval sets the flush interval.
func WithFlushInterval(d time.Duration) Option {
	return func(c *Config) {
		c.FlushInterval = d
	}
}

// WithHTTPClient sets a custom HTTP client.
func WithHTTPClient(cli *http.Client) Option {
	return func(c *Config) {
		c.HTTPClient = cli
	}
}

// WithSource sets the source identifier.
func WithSource(source string) Option {
	return func(c *Config) {
		c.Source = source
	}
}

// Emit adds an event to the batch and flushes if the batch is full.
func (c *Client) Emit(ctx context.Context, event *Event) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if c.closed {
		return fmt.Errorf("client is closed")
	}

	// Apply defaults from config
	if event.Environment == "" {
		event.Environment = c.config.Environment
	}
	if event.Source == "" {
		event.Source = c.config.Source
	}

	c.batch = append(c.batch, event)

	if len(c.batch) >= c.config.BatchSize {
		return c.flushLocked(ctx)
	}

	return nil
}

// Track emits an auto-instrumented event (entity/record_id enriched server-side).
func (c *Client) Track(ctx context.Context, action string, outcome Outcome, opts ...EventOption) error {
	event := NewEvent(action, outcome, opts...)
	return c.Emit(ctx, event)
}

// EmitError emits an error event with the given exception details.
func (c *Client) EmitError(ctx context.Context, entity, action string, err error, category ErrorCategory) error {
	event := NewEvent(action, OutcomeError,
		WithEntity(entity),
		WithError(err.Error(), "", fmt.Sprintf("%T", err), category, nil),
	)
	return c.Emit(ctx, event)
}

// Flush sends all pending events to the backend.
func (c *Client) Flush(ctx context.Context) error {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.flushLocked(ctx)
}

// flushLocked sends all pending events (must be called with lock held).
func (c *Client) flushLocked(ctx context.Context) error {
	if len(c.batch) == 0 {
		return nil
	}

	events := c.batch
	c.batch = make([]*Event, 0, c.config.BatchSize)

	return c.sendEvents(ctx, events)
}

// sendEvents sends events to the backend.
func (c *Client) sendEvents(ctx context.Context, events []*Event) error {
	if len(events) == 0 {
		return nil
	}

	payload, err := json.Marshal(map[string]interface{}{
		"events": events,
	})
	if err != nil {
		return fmt.Errorf("failed to marshal events: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.config.Endpoint, bytes.NewReader(payload))
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+c.config.APIKey)
	req.Header.Set("X-INEV-SDK", c.config.Source)

	resp, err := c.httpCli.Do(req)
	if err != nil {
		return fmt.Errorf("failed to send events: %w", err)
	}
	defer func() {
		_ = resp.Body.Close()
	}()

	if resp.StatusCode >= 400 {
		return fmt.Errorf("backend returned status %d", resp.StatusCode)
	}

	return nil
}

// backgroundFlush periodically flushes events.
func (c *Client) backgroundFlush() {
	defer c.flushWg.Done()

	ticker := time.NewTicker(c.config.FlushInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			_ = c.Flush(ctx)
			cancel()
		case <-c.closeCh:
			return
		}
	}
}

// Close flushes any pending events and closes the client.
func (c *Client) Close(ctx context.Context) error {
	c.mu.Lock()
	if c.closed {
		c.mu.Unlock()
		return nil
	}
	c.closed = true
	close(c.closeCh)
	err := c.flushLocked(ctx)
	c.mu.Unlock()

	c.flushWg.Wait()
	return err
}

// Environment returns the configured environment.
func (c *Client) Environment() string {
	return c.config.Environment
}

// Source returns the configured source.
func (c *Client) Source() string {
	return c.config.Source
}
