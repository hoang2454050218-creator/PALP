import logging
import re

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("palp.privacy")

CONSENT_REQUIRED_PATHS = {
    r"^/api/events/track": "behavioral",
    r"^/api/events/batch": "behavioral",
    r"^/api/events/my": "behavioral",
    r"^/api/adaptive/submit": "behavioral",
    r"^/api/adaptive/mastery": "inference",
    r"^/api/adaptive/pathway": "inference",
    r"^/api/adaptive/interventions": "inference",
    r"^/api/wellbeing/": "behavioral",
}

AUDITED_PATH_PATTERNS = [
    (r"^/api/events/student/(?P<student_id>\d+)", "events.student_events"),
    (r"^/api/assessment/profile/\d+/student/(?P<student_id>\d+)", "assessment.student_profile"),
    (r"^/api/adaptive/student/(?P<student_id>\d+)/mastery", "adaptive.student_mastery"),
    (r"^/api/dashboard/class/(?P<class_id>\d+)/overview", "dashboard.class_overview"),
    (r"^/api/privacy/export", "privacy.export"),
]


class ConsentGateMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return None

        if not getattr(request.user, "is_student", False):
            return None

        path = request.path
        for pattern, purpose in CONSENT_REQUIRED_PATHS.items():
            if re.match(pattern, path):
                from .services import has_consent
                if not has_consent(request.user, purpose):
                    return JsonResponse(
                        {
                            "detail": (
                                f"Bạn cần đồng ý thu thập dữ liệu "
                                f"'{purpose}' để sử dụng tính năng này."
                            ),
                            "consent_required": purpose,
                        },
                        status=403,
                    )
                break
        return None


class AuditMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return response

        if response.status_code >= 400:
            return response

        if request.method not in ("GET", "POST"):
            return response

        path = request.path

        for pattern, resource_name in AUDITED_PATH_PATTERNS:
            match = re.match(pattern, path)
            if match:
                from .services import get_client_ip, log_audit

                detail = {"method": request.method, "path": path}
                detail.update(match.groupdict())

                target_user_id = match.groupdict().get("student_id")
                target_user = None
                if target_user_id:
                    from accounts.models import User
                    target_user = User.objects.filter(id=target_user_id).first()

                log_audit(
                    actor=request.user,
                    action="view",
                    resource=resource_name,
                    target_user=target_user,
                    detail=detail,
                    ip_address=get_client_ip(request),
                    request_id=getattr(request, "request_id", None),
                )
                break

        return response


class PIIScrubLogFilter(logging.Filter):
    PATTERNS = [
        (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL]"),
        (re.compile(r"\b0\d{9,10}\b"), "[PHONE]"),
        (re.compile(r"\b\d{8,10}\b"), "[STUDENT_ID]"),
    ]

    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = self._scrub(record.msg)
        if record.args:
            record.args = tuple(
                self._scrub(str(a)) if isinstance(a, str) else a
                for a in record.args
            )
        return True

    def _scrub(self, text):
        for pattern, replacement in self.PATTERNS:
            text = pattern.sub(replacement, text)
        return text
