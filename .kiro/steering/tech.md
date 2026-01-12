# Technology Stack

## Architecture

Async-first Python SDK with layered architecture:
- **Core Client** - `INEVClient` with async/sync modes, batching, and background flush
- **Integrations Layer** - Framework-specific middleware (FastAPI/Starlette primary)
- **Utils Layer** - Shared logic for action naming, entity extraction, state inference

## Core Technologies

- **Language**: Python 3.10+ (uses `|` union types, modern type hints)
- **HTTP Client**: httpx (async-first, both sync and async support)
- **Framework Support**: FastAPI/Starlette via `BaseHTTPMiddleware`
- **Build System**: Hatchling

## Key Libraries

- **httpx** - Core HTTP client for event transmission
- **starlette** - Base for middleware integration (FastAPI compatible)
- **pytest + pytest-asyncio** - Testing framework

## Development Standards

### Type Safety
- Modern Python type hints (`str | None` syntax)
- No external type checking enforced, but consistent annotation throughout

### Code Quality
- **Ruff** for linting and formatting (line length: 120)
- **pre-commit** hooks for consistency
- Import sorting via isort (first-party: `inev_sdk`)

### Testing
- pytest with asyncio support
- Tests mirror source structure in `/tests/`
- Mock external HTTP calls

## Development Environment

### Required Tools
- Python 3.10+
- uv (preferred) or pip for dependency management
- pre-commit for hooks

### Common Commands
```bash
# Install deps
uv sync

# Run tests
uv run pytest

# Lint/format
uv run ruff check .
uv run ruff format .
```

## Key Technical Decisions

- **Async Context Manager Pattern** - `INEVClient` uses `async with` for lifecycle management
- **Background Flush Task** - Dedicated asyncio task for time-based event flushing
- **Lock-Protected Batching** - `asyncio.Lock` prevents race conditions in batch operations
- **Graceful Degradation** - Event emission failures never break request processing
- **SDK Source Tagging** - All events include `source: "inev-python-sdk"` for origin tracking

---
_Document standards and patterns, not every dependency_
