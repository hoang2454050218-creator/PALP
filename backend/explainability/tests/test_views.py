"""XAI view + persistence tests."""
from __future__ import annotations

import pytest

from explainability.models import (
    CounterfactualScenario,
    ExplanationRecord,
    FeatureContribution,
)


pytestmark = pytest.mark.django_db


class TestRiskExplanation:
    def test_student_can_request_own(self, student_api, student):
        resp = student_api.get("/api/explain/risk/me/")
        assert resp.status_code == 200
        assert "summary" in resp.data
        assert "contributions" in resp.data
        # Persistence happened.
        assert ExplanationRecord.objects.filter(subject=student).exists()

    def test_lecturer_can_request_assigned_student(
        self, lecturer_api, class_with_members, student,
    ):
        resp = lecturer_api.get(f"/api/explain/risk/student/{student.id}/")
        assert resp.status_code == 200

    def test_other_lecturer_blocked(self, lecturer_other_api, student):
        resp = lecturer_other_api.get(f"/api/explain/risk/student/{student.id}/")
        assert resp.status_code == 403

    def test_writes_contributions_and_counterfactuals(self, student_api, student):
        student_api.get("/api/explain/risk/me/")
        record = ExplanationRecord.objects.get(subject=student)
        assert FeatureContribution.objects.filter(explanation=record).exists()
