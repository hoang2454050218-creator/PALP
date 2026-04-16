"""
Utility functions for audit logging.
Uses the AuditLog model from the privacy app.
"""
import logging

logger = logging.getLogger("palp.audit")


def log_audit(
    action,
    request=None,
    user=None,
    target_user=None,
    target_model="",
    target_id="",
    metadata=None,
    status_code=None,
):
    from privacy.models import AuditLog

    ip = _get_client_ip(request) if request else None
    path = request.path if request else ""

    if user is None and request and hasattr(request, "user") and request.user.is_authenticated:
        user = request.user

    request_id = None
    if request and hasattr(request, "request_id"):
        request_id = request.request_id

    action_map = {
        "view_data": AuditLog.Action.VIEW,
        "export_data": AuditLog.Action.EXPORT,
        "delete_data": AuditLog.Action.DELETE,
        "login": AuditLog.Action.VIEW,
        "logout": AuditLog.Action.VIEW,
        "login_failed": AuditLog.Action.VIEW,
        "role_change": AuditLog.Action.VIEW,
        "consent_change": AuditLog.Action.CONSENT_CHANGE,
        "dismiss_alert": AuditLog.Action.VIEW,
        "create_intervention": AuditLog.Action.VIEW,
        "update_rule": AuditLog.Action.VIEW,
    }
    mapped_action = action_map.get(action, AuditLog.Action.VIEW)

    resource = f"{target_model}:{target_id}" if target_model else path

    detail = metadata or {}
    if status_code is not None:
        detail["status_code"] = status_code
    detail["original_action"] = action

    entry = AuditLog.objects.create(
        actor=user,
        action=mapped_action,
        target_user=target_user,
        resource=resource[:200],
        detail=detail,
        ip_address=ip,
        request_id=request_id,
    )

    logger.info(
        "AUDIT action=%s user=%s path=%s target=%s:%s",
        action,
        user.username if user else "anon",
        path,
        target_model,
        target_id,
    )
    return entry


def _get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
