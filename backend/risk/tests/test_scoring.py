from datetime import timedelta

import pytest
from django.utils import timezone

from adaptive.models import MasteryState, MetacognitiveJudgment, TaskAttempt
from events.models import EventLog
from privacy.models import ConsentRecord
from risk.models import RiskScore
from risk.scoring import compute_risk_score

pytestmark = pytest.mark.django_db


@pytest.fixture
def inference_consent(student):
    ConsentRecord.objects.create(user=student, purpose="inference", granted=True, version="1.1")
    return student


class TestComputeRiskScoreColdStart:
    def test_brand_new_student_low_risk(self, student, course):
        result = compute_risk_score(student, course=course, persist=False)
        assert 0.0 <= result.composite <= 30.0
        assert all(0.0 <= v <= 1.0 for v in result.dimensions.values())

    def test_persists_when_requested(self, student, course):
        compute_risk_score(student, course=course, persist=True)
        assert RiskScore.objects.filter(student=student).exists()

    def test_no_persist_when_disabled(self, student, course):
        compute_risk_score(student, course=course, persist=False)
        assert not RiskScore.objects.filter(student=student).exists()


class TestAcademicDimension:
    def test_low_mastery_raises_academic_score(self, student, course, concepts):
        for c in concepts:
            MasteryState.objects.create(student=student, concept=c, p_mastery=0.1)
        result = compute_risk_score(student, course=course, persist=False)
        assert result.dimensions["academic"] > 0.3

    def test_high_mastery_keeps_academic_low(self, student, course, concepts, micro_tasks):
        for c in concepts:
            MasteryState.objects.create(student=student, concept=c, p_mastery=0.95)
        # Also need pathway with some milestones completed to keep lag low
        from adaptive.models import StudentPathway
        StudentPathway.objects.create(
            student=student, course=course, current_concept=concepts[0],
            milestones_completed=[1, 2, 3, 4, 5],
        )
        result = compute_risk_score(student, course=course, persist=False)
        assert result.dimensions["academic"] < 0.5


class TestEngagementDimension:
    def test_inactivity_pushes_engagement_up(self, student, course):
        old_activity = timezone.now() - timedelta(days=10)
        EventLog.objects.create(
            actor=student, actor_type="student",
            event_name="page_view", timestamp_utc=old_activity,
        )
        result = compute_risk_score(student, course=course, persist=False)
        assert result.dimensions["engagement"] > 0.3


class TestMetacognitiveDimension:
    def test_overconfidence_pattern_raises_metacog(self, student, course, micro_tasks):
        for _ in range(10):
            MetacognitiveJudgment.objects.create(
                student=student, task=micro_tasks[0], confidence_pre=5,
                actual_correct=False, calibration_error=1.0,
            )
        result = compute_risk_score(student, course=course, persist=False)
        assert result.dimensions["metacognitive"] > 0.4

    def test_no_judgments_keeps_metacog_zero(self, student, course):
        result = compute_risk_score(student, course=course, persist=False)
        assert result.dimensions["metacognitive"] == 0.0


class TestComposite:
    def test_composite_in_range(self, student, course):
        result = compute_risk_score(student, course=course, persist=False)
        assert 0.0 <= result.composite <= 100.0

    def test_explanation_lists_top_drivers(self, student, course, concepts):
        for c in concepts:
            MasteryState.objects.create(student=student, concept=c, p_mastery=0.05)
        result = compute_risk_score(student, course=course, persist=False)
        assert isinstance(result.explanation, list)
        assert all("dimension" in e and "contribution_pct" in e for e in result.explanation)

    def test_weights_must_sum_to_one(self, student, course, monkeypatch):
        from django.conf import settings
        broken = {"academic": 0.5, "behavioral": 0.5, "engagement": 0.5, "psychological": 0.5, "metacognitive": 0.5}
        monkeypatch.setattr(settings, "PALP_RISK_WEIGHTS", broken)
        with pytest.raises(ValueError, match="sum to 1.0"):
            compute_risk_score(student, course=course, persist=False)


class TestRiskAPI:
    def test_my_risk_returns_composite_only(self, inference_consent, student_api):
        resp = student_api.get("/api/risk/me/")
        assert resp.status_code == 200
        assert "composite" in resp.data
        assert "explanation" in resp.data
        assert "components" not in resp.data
        assert "dimensions" not in resp.data

    def test_my_risk_requires_consent(self, student_api):
        resp = student_api.get("/api/risk/me/")
        assert resp.status_code == 403

    def test_anon_blocked(self, anon_api):
        resp = anon_api.get("/api/risk/me/")
        assert resp.status_code in (401, 403)

    def test_lecturer_sees_full_breakdown_for_assigned_student(
        self, class_with_members, lecturer_api, student
    ):
        resp = lecturer_api.get(f"/api/risk/student/{student.id}/")
        assert resp.status_code == 200
        for key in ("composite", "dimensions", "components", "explanation"):
            assert key in resp.data

    def test_lecturer_blocked_for_unassigned_student(
        self, lecturer_other_api, student, class_with_members
    ):
        resp = lecturer_other_api.get(f"/api/risk/student/{student.id}/")
        assert resp.status_code in (403, 404)

    def test_history_returns_recent_snapshots(self, class_with_members, lecturer_api, student):
        compute_risk_score(student, persist=True)
        compute_risk_score(student, persist=True)
        resp = lecturer_api.get(f"/api/risk/student/{student.id}/history/")
        assert resp.status_code == 200
        assert resp.data["history"]
        for row in resp.data["history"]:
            assert "composite" in row and "severity" in row
