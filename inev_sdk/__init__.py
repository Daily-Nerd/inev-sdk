"""INEV SDK for domain event capture and auto-instrumentation."""

from .client import SDK_SOURCE, INEVClient
from .context import InstrumentationContext
from .decorators import configure, emit_domain_event

# Framework integrations are available but not auto-imported
# Import explicitly: from inev_sdk.integrations.fastapi import INEVMiddleware

__all__ = [
    "INEVClient",
    "SDK_SOURCE",
    "configure",
    "emit_domain_event",
    "InstrumentationContext",
]
__version__ = "0.3.0"
