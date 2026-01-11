# Project Structure

## Organization Philosophy

**Flat package with layered concerns** - The SDK uses a minimal, flat structure with clear separation between core functionality, framework integrations, and shared utilities.

## Directory Patterns

### Package Root (`/inev_sdk/`)
**Purpose**: Core SDK functionality
**Contains**: Client, context manager, decorators, package exports
**Example**: `client.py` (INEVClient), `context.py` (InstrumentationContext)

### Integrations (`/inev_sdk/integrations/`)
**Purpose**: Framework-specific middleware and adapters
**Contains**: One file per framework (fastapi.py, django.py, flask.py)
**Pattern**: Each integration wraps the core client for framework idioms
**Example**: `INEVMiddleware` extends `BaseHTTPMiddleware`

### Utilities (`/inev_sdk/utils/`)
**Purpose**: Shared extraction and inference logic
**Contains**: Pure functions for URL parsing, action naming, state inference
**Pattern**: Stateless utilities that can be used by any integration
**Example**: `generate_action_name()`, `extract_entity_and_record_id()`

### Tests (`/tests/`)
**Purpose**: Test suite mirroring source structure
**Pattern**: `test_<module>.py` for each source module
**Example**: `test_client.py`, `test_fastapi_middleware.py`

### Examples (`/examples/`)
**Purpose**: Usage examples and demos

## Naming Conventions

- **Files**: snake_case (`action_naming.py`, `state_inference.py`)
- **Classes**: PascalCase (`INEVClient`, `InstrumentationContext`, `INEVMiddleware`)
- **Functions**: snake_case (`emit_domain_event`, `generate_action_name`)
- **Constants**: UPPER_SNAKE_CASE (`SDK_SOURCE`, `EXCEPTION_CATEGORY_MAP`)

## Import Organization

```python
# Standard library
import asyncio
from datetime import datetime, timezone

# Third-party
import httpx
from starlette.middleware.base import BaseHTTPMiddleware

# Local (relative within package)
from .client import INEVClient
from ..utils.action_naming import generate_action_name
```

**Path Patterns**:
- Relative imports within package (`from .client import ...`)
- Integrations not auto-imported (explicit: `from inev_sdk.integrations.fastapi import ...`)

## Code Organization Principles

1. **Core exports in `__init__.py`** - Public API defined via `__all__`
2. **Integrations are opt-in** - Not imported by default to avoid framework dependencies
3. **Utils are pure functions** - No state, no side effects, easily testable
4. **One class per file for major components** - Client, Context, Middleware each in own file
5. **Constants near related code** - `EXCEPTION_CATEGORY_MAP` in `client.py` where it's used

---
_Document patterns, not file trees. New files following patterns shouldn't require updates_
