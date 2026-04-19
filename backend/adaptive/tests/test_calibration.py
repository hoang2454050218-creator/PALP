import pytest

from adaptive.calibration import (
    calibration_error_avg,
    finalise_judgment,
    overconfidence_pattern,
    record_judgment,
)
from adaptive.models import MetacognitiveJudgment, TaskAttempt
from privacy.models import ConsentRecord

pytestmark = pytest.mark.django_db


@pytest.fixture
def calibration_consent(student):
    ConsentRecord.objects.create(
        user=student, purpose="cognitive_calibration", granted=True, version="1.1",
    )
    return student


def _attempt(student, task, *, is_correct=True):
    return TaskAttempt.objects.create(
        student=student, task=task, score=1.0 if is_correct else 0.0,
        max_score=1.0, is_correct=is_correct,
    )


class TestRecordJudgment:
    def test_persists(self, student, micro_tasks):
        j = record_judgment(student=student, task=micro_tasks[0], confidence_pre=4)
        assert j.pk is not None
        assert j.confidence_pre == 4
        assert j.actual_correct is None
        assert j.judgment_type == MetacognitiveJudgment.JudgmentType.JOL

    def test_rejects_out_of_range(self, student, micro_tasks):
        with pytest.raises(ValueError, match="1..5"):
            record_judgment(student=student, task=micro_tasks[0], confidence_pre=6)


class TestFinaliseJudgment:
    def test_correct_high_confidence_low_error(self, student, micro_tasks):
        j = record_judgment(student=student, task=micro_tasks[0], confidence_pre=5)
        attempt = _attempt(student, micro_tasks[0], is_correct=True)
        finalise_judgment(judgment=j, task_attempt=attempt)
        j.refresh_from_db()
        assert j.actual_correct is True
        # confidence 5 -> normalised 1.0; actual 1.0; error = 0
        assert j.calibration_error == 0.0

    def test_overconfident_wrong_high_error(self, student, micro_tasks):
        j = record_judgment(student=student, task=micro_tasks[0], confidence_pre=5)
        attempt = _attempt(student, micro_tasks[0], is_correct=False)
        finalise_judgment(judgment=j, task_attempt=attempt)
        j.refresh_from_db()
        # confidence 5 -> normalised 1.0; actual 0.0; error = 1.0
        assert j.calibration_error == 1.0

    def test_idempotent(self, student, micro_tasks):
        j = record_judgment(student=student, task=micro_tasks[0], confidence_pre=3)
        attempt = _attempt(student, micro_tasks[0], is_correct=True)
        finalise_judgment(judgment=j, task_attempt=attempt)
        # Second finalise should not throw and not change values
        before = j.calibration_error
        finalise_judgment(judgment=j, task_attempt=attempt)
        j.refresh_from_db()
        assert j.calibration_error == before


class TestOverconfidencePattern:
    def test_insufficient_data(self, student, micro_tasks):
        judgments = []
        for _ in range(3):
            j = record_judgment(student=student, task=micro_tasks[0], confidence_pre=5)
            attempt = _attempt(student, micro_tasks[0], is_correct=False)
            j.task_attempt = attempt
            j.actual_correct = False
            j.compute_calibration_error()
            j.save()
            judgments.append(j)
        result = overconfidence_pattern(judgments)
        assert result["label"] == "insufficient_data"

    def test_diagnoses_overconfidence(self, student, micro_tasks):
        judgments = []
        for _ in range(10):
            j = MetacognitiveJudgment.objects.create(
                student=student, task=micro_tasks[0], confidence_pre=5,
                actual_correct=False, calibration_error=1.0,
            )
            judgments.append(j)
        result = overconfidence_pattern(judgments)
        assert result["label"] == "overconfident"
        assert result["overconfidence_rate"] >= 0.30

    def test_diagnoses_underconfidence(self, student, micro_tasks):
        judgments = []
        for _ in range(10):
            j = MetacognitiveJudgment.objects.create(
                student=student, task=micro_tasks[0], confidence_pre=2,
                actual_correct=True, calibration_error=0.75,
            )
            judgments.append(j)
        result = overconfidence_pattern(judgments)
        assert result["label"] == "underconfident"

    def test_well_calibrated(self, student, micro_tasks):
        judgments = []
        for i in range(10):
            j = MetacognitiveJudgment.objects.create(
                student=student, task=micro_tasks[0], confidence_pre=3,
                actual_correct=(i % 2 == 0), calibration_error=0.5,
            )
            judgments.append(j)
        result = overconfidence_pattern(judgments)
        assert result["label"] == "well_calibrated"


class TestCalibrationView:
    def test_anon_rejected(self, anon_api):
        resp = anon_api.post("/api/adaptive/calibration/", data={}, format="json")
        assert resp.status_code in (401, 403)

    def test_no_consent_403(self, student_api, micro_tasks):
        resp = student_api.post(
            "/api/adaptive/calibration/",
            data={"task_id": micro_tasks[0].id, "confidence_pre": 4},
            format="json",
        )
        assert resp.status_code == 403

    def test_with_consent_creates(self, student_api, calibration_consent, micro_tasks):
        resp = student_api.post(
            "/api/adaptive/calibration/",
            data={"task_id": micro_tasks[0].id, "confidence_pre": 4},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["confidence_pre"] == 4
        assert MetacognitiveJudgment.objects.filter(student=calibration_consent).exists()

    def test_unknown_task_400(self, student_api, calibration_consent):
        resp = student_api.post(
            "/api/adaptive/calibration/",
            data={"task_id": 99999, "confidence_pre": 4},
            format="json",
        )
        assert resp.status_code == 400

    def test_my_calibration_returns_diagnosis(self, student_api, calibration_consent, micro_tasks):
        for _ in range(6):
            student_api.post(
                "/api/adaptive/calibration/",
                data={"task_id": micro_tasks[0].id, "confidence_pre": 5},
                format="json",
            )
        resp = student_api.get("/api/adaptive/calibration/me/")
        assert resp.status_code == 200
        assert "diagnosis" in resp.data
        assert "recent" in resp.data
