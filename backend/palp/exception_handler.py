"""
Unified API exception handler for PALP.

Every error response follows the envelope:

    {
        "error": {
            "code":       "<MACHINE_READABLE>",
            "message":    "<human-readable, Vietnamese preferred>",
            "details":    { ... },           # field-level errors on 400
            "request_id": "<uuid>"
        }
    }

Guarantees:
- Validation errors never become 500.
- Stack traces / internal paths never leak to the client.
- PII (email, phone) is scrubbed from every error payload.
- ``request_id`` is injected from ``RequestIDMiddleware``.
"""

import logging
import re

from django.core.exceptions import (
    PermissionDenied as DjangoPermissionDenied,
)
from django.core.exceptions import (
    ValidationError as DjangoValidationError,
)
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from .error_codes import HTTP_STATUS_TO_CODE, ErrorCode

logger = logging.getLogger("palp")

PII_PATTERNS = [
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}"), "[EMAIL]"),
    (re.compile(r"\b0\d{9,10}\b"), "[PHONE]"),
]

_DEFAULT_MESSAGES = {
    401: "Xác thực không thành công.",
    403: "Bạn không có quyền truy cập.",
    404: "Không tìm thấy tài nguyên yêu cầu.",
    405: "Phương thức HTTP không được hỗ trợ.",
    429: "Quá nhiều yêu cầu. Vui lòng thử lại sau.",
}

_INTERNAL_ERROR_MSG = "Đã xảy ra lỗi hệ thống. Vui lòng thử lại sau."


def palp_exception_handler(exc, context):
    """DRF ``EXCEPTION_HANDLER`` entry-point."""

    if isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError(detail=exc.messages)
    elif isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    response = drf_exception_handler(exc, context)

    request = context.get("request")
    request_id = _get_request_id(request)

    if response is not None:
        response.data = _build_envelope(response, request_id)
        _scrub_pii(response.data)
        return response

    logger.exception(
        "Unhandled exception in %s [rid=%s]",
        context.get("view"),
        request_id,
    )

    body = {
        "error": {
            "code": ErrorCode.INTERNAL_ERROR,
            "message": _INTERNAL_ERROR_MSG,
            "request_id": request_id,
        }
    }
    return Response(body, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _build_envelope(response, request_id):
    """Normalise any DRF error payload into the standard envelope."""
    status_code = response.status_code
    data = response.data

    if status_code >= 500:
        return {
            "error": {
                "code": ErrorCode.INTERNAL_ERROR,
                "message": _INTERNAL_ERROR_MSG,
                "request_id": request_id,
            }
        }

    code = HTTP_STATUS_TO_CODE.get(status_code, ErrorCode.INTERNAL_ERROR)
    message = _DEFAULT_MESSAGES.get(status_code, "")
    details = {}

    if isinstance(data, dict):
        explicit_detail = data.pop("detail", None)
        if explicit_detail:
            message = (
                str(explicit_detail)
                if not isinstance(explicit_detail, list)
                else "; ".join(str(m) for m in explicit_detail)
            )
        if data:
            details = data
    elif isinstance(data, list):
        message = "; ".join(str(item) for item in data)

    if status_code == 400 and not message:
        message = "Dữ liệu không hợp lệ."

    envelope = {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
        }
    }
    if details:
        envelope["error"]["details"] = details

    return envelope


def _get_request_id(request):
    if request is None:
        return None
    rid = getattr(request, "request_id", None)
    return str(rid) if rid else None


def _scrub_pii(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str):
                data[key] = _scrub_string(value)
            elif isinstance(value, (dict, list)):
                _scrub_pii(value)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, str):
                data[i] = _scrub_string(item)
            elif isinstance(item, (dict, list)):
                _scrub_pii(item)


def _scrub_string(text):
    for pattern, replacement in PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text
