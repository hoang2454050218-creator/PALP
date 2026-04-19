"""HTTP endpoints for the XAI layer.

| Method | Path                              | Auth                   |
| ------ | --------------------------------- | ---------------------- |
| GET    | ``risk/me/``                       | IsStudent (own)        |
| GET    | ``risk/student/<id>/``             | IsLecturerOfStudent    |
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import (
    IsLecturer,
    IsStudent,
    IsStudentInLecturerClass,
)

from explainability.services import explain_and_persist_risk


def _serialize(record):
    return {
        "id": record.id,
        "kind": record.kind,
        "method": record.method,
        "summary": record.summary,
        "score": record.payload.get("score"),
        "base_value": record.base_value,
        "contributions": [
            {
                "feature_key": c.feature_key,
                "raw_value": c.raw_value,
                "contribution": c.contribution,
                "rank": c.rank,
            }
            for c in record.contributions.all().order_by("rank")
        ],
        "counterfactuals": [
            {
                "feature_key": cf.feature_key,
                "current_value": cf.current_value,
                "target_value": cf.target_value,
                "expected_delta": cf.expected_delta,
                "feasibility": cf.feasibility,
                "actionable_hint": cf.actionable_hint,
            }
            for cf in record.counterfactuals.all().order_by("-feasibility")
        ],
        "created_at": record.created_at,
    }


def _explain_risk_for(student):
    from risk.scoring import compute_risk_score

    snapshot = compute_risk_score(student, persist=False)
    record = explain_and_persist_risk(student=student, snapshot=snapshot)
    return record


class MyRiskExplanationView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        record = _explain_risk_for(request.user)
        return Response(_serialize(record))


class StudentRiskExplanationView(APIView):
    permission_classes = [
        IsAuthenticated, IsLecturer, IsStudentInLecturerClass,
    ]

    def get(self, request, student_id):
        from accounts.models import User

        student = User.objects.filter(id=student_id, role=User.Role.STUDENT).first()
        if not student:
            return Response(
                {"detail": "Không tìm thấy sinh viên."},
                status=status.HTTP_404_NOT_FOUND,
            )
        record = _explain_risk_for(student)
        return Response(_serialize(record))
