"""
Per-event JSON schemas for ``EventLog.properties`` validation.

Each event_name added in v3 roadmap (Phase 1+) has a corresponding
``<event_name>.json`` file in this directory describing the shape of its
``properties`` dict. ``events.emitter.emit_event`` calls
``validate_properties()`` before persisting to keep the analytics schema
clean.

Schemas follow JSON Schema Draft 7. The validator falls back to
no-op when ``jsonschema`` is not installed so the runtime cost of the
contract is opt-in: production deployments install jsonschema, dev
machines can skip it.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger("palp.events")

_SCHEMAS_DIR = Path(__file__).resolve().parent


class SchemaValidationError(ValueError):
    """Raised when ``properties`` doesn't match the registered schema."""


@lru_cache(maxsize=128)
def _load_schema(event_name: str) -> dict | None:
    path = _SCHEMAS_DIR / f"{event_name}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.exception("Malformed JSON schema for %s", event_name)
        return None


def has_schema(event_name: str) -> bool:
    return _load_schema(event_name) is not None


def validate_properties(event_name: str, properties: dict) -> None:
    """Validate ``properties`` against the registered schema.

    No-op when:
      * the event has no schema file (legacy event_name without contract).
      * the ``jsonschema`` library is not installed.

    Raises ``SchemaValidationError`` when the payload violates the schema.
    """
    schema = _load_schema(event_name)
    if schema is None:
        return
    try:
        import jsonschema  # type: ignore
    except ImportError:
        logger.debug(
            "jsonschema not installed; skipping payload validation for %s",
            event_name,
        )
        return
    try:
        jsonschema.validate(instance=properties or {}, schema=schema)
    except jsonschema.ValidationError as exc:
        raise SchemaValidationError(
            f"Invalid properties for event_name={event_name!r}: {exc.message}"
        ) from exc


def reset_cache() -> None:
    """Clear the lru_cache (test helper / hot reload)."""
    _load_schema.cache_clear()
