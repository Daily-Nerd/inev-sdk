# INEV SDK for Go

Intentionality Leakage Analysis (ILA) event capture SDK for Go applications. Automatically tracks user behavior, detects trajectory gaps, and identifies error leaks with minimal code changes.

## Installation

```bash
go get github.com/Daily-Nerd/inev-sdk-go
```

## Quick Start

### Basic Usage

```go
package main

import (
    "context"
    "log"

    "github.com/Daily-Nerd/inev-sdk-go/client"
)

func main() {
    // Create a new client
    c := client.New("your-api-key",
        client.WithEnvironment("production"),
        client.WithBatchSize(50),
    )
    defer c.Close(context.Background())

    // Emit an event
    event := client.NewEvent("create_order", client.OutcomeSuccess,
        client.WithEntity("order"),
        client.WithRecordID("ord_123"),
        client.WithToState("created"),
        client.WithUserID("user_456"),
    )

    if err := c.Emit(context.Background(), event); err != nil {
        log.Printf("Failed to emit event: %v", err)
    }
}
```

### Chi Middleware (Auto-Instrumentation)

```go
package main

import (
    "net/http"

    "github.com/go-chi/chi/v5"

    "github.com/Daily-Nerd/inev-sdk-go/client"
    inevchi "github.com/Daily-Nerd/inev-sdk-go/integrations/chi"
)

func main() {
    // Create INEV client
    inevClient := client.New("your-api-key",
        client.WithEnvironment("production"),
    )
    defer inevClient.Close(context.Background())

    // Create Chi router
    r := chi.NewRouter()

    // Add INEV middleware
    cfg := inevchi.DefaultConfig(inevClient)
    cfg.ExcludePaths = append(cfg.ExcludePaths, "/internal")
    r.Use(inevchi.Middleware(cfg))

    // Define routes
    r.Get("/api/users", listUsers)
    r.Post("/api/users", createUser)
    r.Get("/api/users/{id}", getUser)
    r.Delete("/api/users/{id}", deleteUser)

    http.ListenAndServe(":8080", r)
}
```

## Features

### Automatic Action Naming

The SDK automatically derives semantic action names from HTTP requests:

| Method | Path | Action |
|--------|------|--------|
| GET | /api/users | list_users |
| POST | /api/users | create_user |
| GET | /api/users/123 | get_user |
| PUT | /api/users/123 | update_user |
| DELETE | /api/users/123 | delete_user |
| POST | /api/orders/123/confirm | confirm_order |

### Entity Extraction

Entities and record IDs are automatically extracted from REST URLs:

| Path | Entity | Record ID |
|------|--------|-----------|
| /api/users/123 | user | 123 |
| /api/workspaces/ws_123/members | member | - |
| /api/workspaces/ws_123/members/usr_456 | member | usr_456 |

### State Inference

States are inferred from HTTP methods, status codes, and action verbs:

| Context | Inferred State |
|---------|---------------|
| POST + 201 | created |
| PUT/PATCH + 200 | updated |
| DELETE + 204 | deleted |
| action: confirm_order | confirmed |
| action: approve_request | approved |
| action: ship_order | shipped |

### Error Categorization

HTTP status codes are mapped to error categories:

| Status Code | Category |
|-------------|----------|
| 400 | validation |
| 401, 403 | auth |
| 404 | not_found |
| 429 | rate_limit |
| 5xx | server |

## Configuration Options

### Client Options

```go
client.New("api-key",
    client.WithEndpoint("https://custom.inev.io/v1/events"),
    client.WithEnvironment("staging"),
    client.WithBatchSize(100),           // Events per batch
    client.WithFlushInterval(5*time.Second),
    client.WithSource("my-service"),
    client.WithHTTPClient(customClient),
)
```

### Event Options

```go
client.NewEvent("action", client.OutcomeSuccess,
    client.WithEntity("order"),
    client.WithRecordID("ord_123"),
    client.WithFromState("pending"),
    client.WithToState("confirmed"),
    client.WithUserID("user_456"),
    client.WithSessionID("sess_789"),
    client.WithParameters(map[string]interface{}{
        "amount": 99.99,
        "currency": "USD",
    }),
    client.WithError("msg", "code", "type", client.ErrorCategoryValidation, nil),
)
```

### Middleware Options

```go
cfg := inevchi.DefaultConfig(client)
cfg.ExcludePaths = []string{"/health", "/metrics"}
cfg.ExcludeExact = []string{"/", "/favicon.ico"}
cfg.UseSemanticActions = true  // "create_user" vs "post_users"

// Custom user ID extraction
cfg.ExtractUserID = func(r *http.Request) string {
    return r.Header.Get("X-Custom-User-ID")
}

// Error callback
cfg.OnError = func(err error) {
    log.Printf("INEV error: %v", err)
}
```

## Utility Packages

### Action Naming

```go
import "github.com/Daily-Nerd/inev-sdk-go/utils"

// HTTP method + path → action name
action := utils.DeriveActionName("POST", "/api/orders")
// → "post_orders"

// Semantic version
action := utils.DeriveSemanticActionName("POST", "/api/orders")
// → "create_order"
```

### Entity Extraction

```go
import "github.com/Daily-Nerd/inev-sdk-go/utils"

info := utils.ExtractEntity("/api/users/123/posts/456")
// info.Entity = "post", info.RecordID = "456"

parent := utils.ExtractParentEntity("/api/users/123/posts/456")
// parent.Entity = "user", parent.RecordID = "123"

all := utils.ExtractAllEntities("/api/users/123/posts/456")
// [{user, 123}, {post, 456}]
```

### State Inference

```go
import "github.com/Daily-Nerd/inev-sdk-go/utils"

state := utils.InferState("POST", 201)
// → "created"

state := utils.InferStateFromAction("confirm_order")
// → "confirmed"

trans := utils.InferFullTransition("POST", 200, "approve_request")
// trans.ToState = "approved"
```

## Event Schema

```json
{
  "event_id": "uuid",
  "timestamp": "2024-01-15T10:30:00Z",
  "entity": "order",
  "action": "create_order",
  "record_id": "ord_123",
  "from_state": null,
  "to_state": "created",
  "outcome": "success",
  "error_message": null,
  "error_code": null,
  "error_type": null,
  "error_category": null,
  "error_details": null,
  "user_id": "user_456",
  "session_id": "sess_789",
  "parameters": {"amount": 99.99},
  "environment": "production",
  "source": "inev-go-sdk"
}
```

## License

MIT
