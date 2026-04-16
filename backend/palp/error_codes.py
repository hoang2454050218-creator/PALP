"""
Stable, machine-readable error codes returned in every API error response.

These codes form part of the public API contract. Removing or renaming an
existing code is a **breaking change** and must go through the API release gate.
"""


class ErrorCode:
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    THROTTLED = "THROTTLED"
    CONFLICT = "CONFLICT"
    DUPLICATE_REQUEST = "DUPLICATE_REQUEST"
    UNSUPPORTED_MEDIA_TYPE = "UNSUPPORTED_MEDIA_TYPE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


HTTP_STATUS_TO_CODE = {
    400: ErrorCode.VALIDATION_ERROR,
    401: ErrorCode.AUTHENTICATION_REQUIRED,
    403: ErrorCode.PERMISSION_DENIED,
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.METHOD_NOT_ALLOWED,
    409: ErrorCode.CONFLICT,
    415: ErrorCode.UNSUPPORTED_MEDIA_TYPE,
    429: ErrorCode.THROTTLED,
}
