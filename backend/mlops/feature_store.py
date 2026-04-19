"""
Lightweight Feast-compatible feature store wrapper.

Online reads served from Redis (``django_redis`` cache backend) when the
underlying ``FeatureView.online_store_enabled`` flag is True; offline reads
are passthrough SQL queries against the source table named in
``FeatureView.source_table``. Promoting to a real Feast deployment later
only requires swapping the cache key prefix for Feast's own client.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Iterable

from django.core.cache import cache

from .models import FeatureView

logger = logging.getLogger("palp")

ONLINE_KEY_PREFIX = "palp:fs:online"
DEFAULT_TTL_SECONDS = 300


def register_view(
    name: str,
    *,
    entity: str,
    source_table: str,
    features: list[dict],
    online_store_enabled: bool = False,
    description: str = "",
) -> FeatureView:
    obj, created = FeatureView.objects.get_or_create(
        name=name,
        defaults={
            "entity": entity,
            "source_table": source_table,
            "features_json": features,
            "online_store_enabled": online_store_enabled,
            "description": description,
        },
    )
    if not created:
        # Allow non-destructive updates (description, features additions, online toggle)
        obj.entity = entity or obj.entity
        obj.source_table = source_table or obj.source_table
        obj.online_store_enabled = online_store_enabled
        if description:
            obj.description = description
        if features:
            existing_names = {f.get("name") for f in obj.features_json or []}
            obj.features_json = list(obj.features_json or []) + [
                f for f in features if f.get("name") not in existing_names
            ]
        obj.save()
    return obj


def _key(view_name: str, entity_id: int | str) -> str:
    return f"{ONLINE_KEY_PREFIX}:{view_name}:{entity_id}"


def push_online(
    view: FeatureView | str,
    entity_id: int | str,
    values: dict[str, Any],
    *,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> None:
    """Write feature values to the online store (Redis).

    No-op if the view has online_store_enabled=False — keeps the call site
    simple for code paths that compute features even when only offline use
    is required.
    """
    if isinstance(view, str):
        try:
            view = FeatureView.objects.get(name=view)
        except FeatureView.DoesNotExist:
            logger.warning("push_online: unknown view %r, ignoring", view)
            return
    if not view.online_store_enabled:
        return
    cache.set(_key(view.name, entity_id), json.dumps(values), ttl_seconds)


def get_online(
    view: FeatureView | str,
    entity_id: int | str,
) -> dict[str, Any] | None:
    if isinstance(view, str):
        try:
            view = FeatureView.objects.get(name=view)
        except FeatureView.DoesNotExist:
            return None
    if not view.online_store_enabled:
        return None
    raw = cache.get(_key(view.name, entity_id))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def get_online_batch(
    view: FeatureView | str,
    entity_ids: Iterable[int | str],
) -> dict[int | str, dict[str, Any] | None]:
    return {eid: get_online(view, eid) for eid in entity_ids}
