"""Shared Cypher utility functions for injection prevention.

Used by retrieval/graph.py, retrieval/entity_centric.py, graph/client.py.
Eliminates duplicate _safe_identifier and _validate_int copies.
"""

import re
from typing import Any

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def safe_identifier(name: str) -> str:
    """Validate identifier for Cypher label/type — prevents injection.

    Args:
        name: The identifier to validate.

    Returns:
        The validated identifier.

    Raises:
        ValueError: If the identifier contains invalid characters.
    """
    if not name or not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid identifier '{name}': must match ^[A-Za-z_][A-Za-z0-9_]*$")
    return name


def validate_int(value: Any, name: str, min_val: int = 1, max_val: int = 100) -> int:
    """Validate an integer parameter for Cypher bounds.

    Args:
        value: The value to validate.
        name: Parameter name for error messages.
        min_val: Minimum allowed value (inclusive).
        max_val: Maximum allowed value (inclusive).

    Returns:
        The validated integer.

    Raises:
        ValueError: If the value is not an integer or out of range.
    """
    try:
        int_val = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid {name}: must be an integer")
    if int_val < min_val or int_val > max_val:
        raise ValueError(f"Invalid {name}: must be between {min_val} and {max_val}")
    return int_val
