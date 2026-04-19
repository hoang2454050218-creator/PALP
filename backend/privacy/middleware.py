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
    # v3 roadmap — Phase 1
    r"^/api/signals/": "behavioral_signals",
    r"^/api/adaptive/calibration": "cognitive_calibration",
    r"^/api/risk/me": "inference",
    # v3 roadmap — Phase 3 (Peer Engine)
    # ``frontier`` and ``consent`` are intentionally NOT gated — frontier
    # is past-self only and consent must always be reachable so the
    # student can opt out of any peer feature without consenting to it
    # first (which would be self-defeating).
    r"^/api/peer/benchmark": "peer_comparison",
    r"^/api/peer/buddy": "peer_teaching",
    r"^/api/peer/teaching-session": "peer_teaching",
    # v3 roadmap — Phase 4 (AI Coach + Emergency Pipeline)
    # ``coach/consent`` and ``coach/conversations`` (read-only history)
    # are intentionally NOT gated so the student can disable the coach
    # and still review past conversations. Sending a new message is
    # gated below.
    r"^/api/coach/message": "ai_coach_local",
    # v3 roadmap — Phase 5 (Agentic memory)
    # ``GET memory/me/`` is gated so the panel does not surface memory
    # the student never agreed to populate. ``DELETE`` is intentionally
    # NOT path-gated so users can always revoke + clear memory even
    # without consent.
    r"^/api/coach/memory/me/$": "agentic_memory",
    # v3 roadmap — Phase 7 (Academic layer)
    # The opt-in/consent endpoints themselves are intentionally NOT
    # gated so a student can always set or revoke participation. We
    # only gate the actual ingestion paths.
    r"^/api/affect/ingest": "affect_signals",
    r"^/api/affect/me": "affect_signals",
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
        # Defense-in-depth: scrub OpenAI/Anthropic/key4u-style secrets so a
        # stray log statement in coach/llm/* never persists a key. The
        # patterns are intentionally broad — false positives are fine,
        # leaked keys are not.
        (re.compile(r"sk-[A-Za-z0-9_\-]{20,}"), "[API_KEY]"),
        (re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"), "[API_KEY]"),
        (re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{20,}"), "Bearer [REDACTED]"),
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
