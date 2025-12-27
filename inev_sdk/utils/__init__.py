"""Utility functions for INEV SDK."""

from .action_naming import (
    generate_action_name,
    generate_semantic_action_name,
    is_id_segment,
    singularize,
)

__all__ = [
    "generate_action_name",
    "generate_semantic_action_name",
    "is_id_segment",
    "singularize",
]
