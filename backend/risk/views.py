"""
RiskScore API endpoints.

* GET /api/risk/me/                — student sees only the composite +
  XAI explanation (no raw component values to avoid Goodhart's gaming).
* GET /api/risk/student/<id>/      — lecturer/admin sees the full
  breakdown for an assigned student. Reuses the existing
  ``IsStudentInLecturerClass`` RBAC gate.
* GET /api/risk/student/<id>/history/ — last N snapshots for charts.
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsLecturerOrAdmin, IsStudent, IsStudentInLecturerClass
from privacy.services import has_consent

from .models import RiskScore
from .scoring import compute_risk_score


class MyRiskScoreView(APIView):
    permission_classes = (IsAuthenticated, IsStudent)

    def get(self, request):
        if not has_consent(request.user, "inference"):
            return Response(
                {"detail": "Bạn cần đồng ý 'inference' để xem RiskScore.",
                 "consent_required": "inference"},
                status=status.HTTP_403_FORBIDDEN,
            )
        breakdown = compute_risk_score(request.user)
        return Response({
            "composite": breakdown.composite,
            "severity": _severity_label(breakdown.composite),
            "explanation": breakdown.explanation,
            "computed_window_days": breakdown.sample_window_days,
        })


class StudentRiskScoreView(APIView):
    permission_classes = (IsAuthenticated, IsLecturerOrAdmin, IsStudentInLecturerClass)

    def get(self, request, student_id):
        try:
            student = User.objects.get(pk=student_id)
        except User.DoesNotExist:
            return Response({"detail": "Student not found."}, status=404)

        breakdown = compute_risk_score(student)
        return Response({
            "student_id": student.id,
            "composite": breakdown.composite,
            "dimensions": breakdown.dimensions,
            "components": breakdown.components,
            "explanation": breakdown.explanation,
            "weights_used": breakdown.weights_used,
            "computed_window_days": breakdown.sample_window_days,
        })


class StudentRiskHistoryView(APIView):
    permission_classes = (IsAuthenticated, IsLecturerOrAdmin, IsStudentInLecturerClass)

    def get(self, request, student_id):
        try:
            student = User.objects.get(pk=student_id)
        except User.DoesNotExist:
            return Response({"detail": "Student not found."}, status=404)

        rows = RiskScore.objects.filter(student=student).order_by("-computed_at")[:30]
        return Response({
            "student_id": student.id,
            "history": [
                {
                    "composite": r.composite,
                    "severity": r.severity,
                    "dimensions": r.dimensions,
                    "computed_at": r.computed_at,
                }
                for r in rows
            ],
        })


def _severity_label(composite: float) -> str:
    from django.conf import settings
    thresholds = settings.PALP_RISK_THRESHOLDS
    if composite >= thresholds["ALERT_RED"]:
        return "red"
    if composite >= thresholds["ALERT_YELLOW"]:
        return "yellow"
    return "green"
