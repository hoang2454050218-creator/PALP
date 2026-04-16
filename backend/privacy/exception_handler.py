"""
Backwards-compatible shim — all logic now lives in ``palp.exception_handler``.
"""

from palp.exception_handler import palp_exception_handler as privacy_exception_handler  # noqa: F401
