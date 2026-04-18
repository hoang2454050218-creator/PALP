"""
Service layer for feature flag evaluation.

Decisions are intentionally pure-function (no side effect, no logging on
hot path) so they can be called from views/middleware millions of times
per day without performance impact.
"""
from __future__ import annotations

import hashlib
import logging

from django.conf import settings
from django.core.cache import cache

from .models import FeatureFlag

logger = logging.getLogger("palp")

CACHE_KEY = "palp:featureflags:v1"
CACHE_TTL = 60  # 1 minute -- balance staleness vs DB load


def _all_flags() -> dict[str, dict]:
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached
    flags = {
        f.name: {
            "enabled": f.enabled,
            "rollout_pct": f.rollout_pct,
            "rules": f.rules_json or {},
        }
        for f in FeatureFlag.objects.all()
    }
    cache.set(CACHE_KEY, flags, CACHE_TTL)
    return flags


def invalidate_cache() -> None:
    cache.delete(CACHE_KEY)


def is_enabled(name: str, user=None, *, env: str | None = None) -> bool:
    """Return True if the flag is enabled for the given user.

    * Master switch ``enabled=False`` always wins (returns False).
    * Targeting rules narrow the audience (role, class_id, env).
    * Rollout percent is a stable hash of (flag, user.id), so the same
      user always falls in the same bucket across navigations.
    """
    flags = _all_flags()
    flag = flags.get(name)
    if not flag or not flag["enabled"]:
        return False

    rules = flag["rules"] or {}
    if "env" in rules and env not in rules["env"]:
        return False
    if "roles" in rules and user is not None:
        role = getattr(user, "role", None)
        if role not in rules["roles"]:
            return False
    if "class_ids" in rules and user is not None:
        member_classes = list(
            getattr(user, "class_memberships", None).values_list(
                "student_class_id", flat=True
            )
            if hasattr(user, "class_memberships")
            else []
        )
        if not any(cid in member_classes for cid in rules["class_ids"]):
            return False

    pct = max(0, min(100, int(flag["rollout_pct"] or 0)))
    if pct >= 100:
        return True
    if pct <= 0:
        return False
    if user is None or not getattr(user, "id", None):
        return False
    bucket = _stable_bucket(name, user.id)
    return bucket < pct


def _stable_bucket(name: str, user_id: int) -> int:
    """Return 0-99 bucket deterministically based on (flag, user_id)."""
    h = hashlib.sha256(f"{name}:{user_id}".encode("utf-8")).hexdigest()
    return int(h[:8], 16) % 100


def active_flags_for(user) -> dict[str, bool]:
    """Compute the public flag map shipped to the frontend.

    Only includes flags whose name doesn't start with ``_internal.`` so we
    don't accidentally leak operations-only switches.
    """
    flags = _all_flags()
    return {
        name: is_enabled(name, user=user)
        for name in flags
        if not name.startswith("_internal.")
    }
