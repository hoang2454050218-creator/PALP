"""
HTTP-level idempotency for write endpoints.

Usage::

    class MyView(APIView):
        @idempotent(required=True)
        def post(self, request):
            ...

When ``required=True`` the client **must** send an ``Idempotency-Key`` header;
omitting it returns 400.  When ``required=False`` the header is optional —
requests without it are executed normally (no caching).

Cached responses live in Redis for ``ttl`` seconds (default 86 400 = 24 h).
A matching key replays the original status code and body verbatim.
"""

import hashlib
import logging
import uuid
from functools import wraps

from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response

from .error_codes import ErrorCode

logger = logging.getLogger("palp")

_DEFAULT_TTL = 86_400
_KEY_PREFIX = "palp:idempotency"
_LOCK_SUFFIX = ":lock"
_LOCK_TTL = 30


def idempotent(required=True, ttl=_DEFAULT_TTL):
    """Decorator that adds ``Idempotency-Key`` semantics to a DRF view method."""

    def decorator(view_method):
        @wraps(view_method)
        def wrapper(view_instance, request, *args, **kwargs):
            raw_key = request.META.get("HTTP_IDEMPOTENCY_KEY", "").strip()

            if not raw_key:
                if required:
                    return Response(
                        {
                            "error": {
                                "code": ErrorCode.VALIDATION_ERROR,
                                "message": "Header Idempotency-Key là bắt buộc cho endpoint này.",
                                "request_id": _rid(request),
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                return view_method(view_instance, request, *args, **kwargs)

            try:
                uuid.UUID(raw_key)
            except ValueError:
                return Response(
                    {
                        "error": {
                            "code": ErrorCode.VALIDATION_ERROR,
                            "message": "Idempotency-Key phải là UUID hợp lệ.",
                            "request_id": _rid(request),
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user_id = getattr(request.user, "pk", "anon")
            cache_key = _cache_key(user_id, raw_key)
            lock_key = cache_key + _LOCK_SUFFIX

            cached = cache.get(cache_key)
            if cached is not None:
                return Response(
                    cached["body"],
                    status=cached["status"],
                    headers={"Idempotency-Replayed": "true"},
                )

            acquired = cache.add(lock_key, "1", _LOCK_TTL)
            if not acquired:
                return Response(
                    {
                        "error": {
                            "code": ErrorCode.CONFLICT,
                            "message": "Yêu cầu trùng đang được xử lý. Vui lòng thử lại.",
                            "request_id": _rid(request),
                        }
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            try:
                response = view_method(view_instance, request, *args, **kwargs)

                if response.status_code < 500:
                    cache.set(
                        cache_key,
                        {"status": response.status_code, "body": response.data},
                        ttl,
                    )

                return response
            finally:
                cache.delete(lock_key)

        wrapper._idempotent = True
        wrapper._idempotent_required = required
        return wrapper

    return decorator


def _cache_key(user_id, raw_key):
    digest = hashlib.sha256(f"{user_id}:{raw_key}".encode()).hexdigest()[:32]
    return f"{_KEY_PREFIX}:{digest}"


def _rid(request):
    rid = getattr(request, "request_id", None)
    return str(rid) if rid else None
