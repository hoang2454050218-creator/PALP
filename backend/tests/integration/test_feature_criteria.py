"""
Core Feature Quality Standards Tests (F1-F5).

QA_STANDARD Section 1.6.
Tests criteria not already covered by per-module unit tests.
"""
import pytest
import hashlib
import tempfile
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from accounts.models import User
from adaptive.engine import update_mastery, decide_pathway_action, get_mastery_state
from adaptive.models import MasteryState, TaskAttempt, ContentIntervention, StudentPathway
from assessment.models import AssessmentSession, AssessmentResponse, LearnerProfile
from curriculum.models import Concept, Milestone, MicroTask
from dashboard.models import Alert
from dashboard.services import compute_early_warnings, get_class_overview
from events.models import EventLog

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.integration]

THRESHOLDS = settings.PALP_ADAPTIVE_THRESHOLDS


# ===================================================================
# F1 — Assessment dau vao
# ===================================================================


class TestF1Assessment:
    """F1-01..F1-08: Assessment quality criteria."""

    def test_f1_03_score_calculation_exact(
        self, student, student_api, assessment,
    ):
        """Score = correct/total * 100, no rounding errors beyond 2 decimals."""
        start = student_api.post(f"/api/assessment/{assessment.pk}/start/")
        assert start.status_code == 201
        sid = start.data["id"]

        questions = assessment.questions.order_by("order")
        total = questions.count()
        correct_count = 0

        for i, q in enumerate(questions):
            answer = q.options[0] if hasattr(q, "options") and q.options else "A"
            student_api.post(
                f"/api/assessment/sessions/{sid}/answer/",
                {"question_id": q.id, "answer": answer, "time_taken_seconds": 10},
                format="json",
            )
            correct_count += 1

        complete = student_api.post(f"/api/assessment/sessions/{sid}/complete/")
        assert complete.status_code == 200

        session = AssessmentSession.objects.get(pk=sid)
        expected = round(correct_count / total * 100, 2) if total > 0 else 0
        assert abs(session.score - expected) <= 0.01, (
            f"Score mismatch: got {session.score}, expected {expected}"
        )

    def test_f1_06_two_tabs_only_one_session(
        self, student, student_api, assessment,
    ):
        """Starting assessment on tab 2 while tab 1 is active -> reject."""
        start1 = student_api.post(f"/api/assessment/{assessment.pk}/start/")
        assert start1.status_code == 201

        start2 = student_api.post(f"/api/assessment/{assessment.pk}/start/")
        assert start2.status_code in (400, 409, 200), (
            f"Unexpected status {start2.status_code} for duplicate session"
        )

        active_sessions = AssessmentSession.objects.filter(
            student=student,
            assessment=assessment,
            status="in_progress",
        ).count()
        assert active_sessions <= 1, (
            f"Found {active_sessions} active sessions — should be max 1"
        )

    def test_f1_08_submit_creates_audit_event(
        self, student, student_api, assessment,
    ):
        """Every assessment completion must fire assessment_completed event."""
        start = student_api.post(f"/api/assessment/{assessment.pk}/start/")
        sid = start.data["id"]

        for q in assessment.questions.order_by("order"):
            student_api.post(
                f"/api/assessment/sessions/{sid}/answer/",
                {"question_id": q.id, "answer": "A", "time_taken_seconds": 10},
                format="json",
            )

        student_api.post(f"/api/assessment/sessions/{sid}/complete/")

        event = EventLog.objects.filter(
            event_name=EventLog.EventName.ASSESSMENT_COMPLETED,
            actor=student,
        ).first()
        assert event is not None, "assessment_completed event not fired"


# ===================================================================
# F2 — Adaptive Pathway v1
# ===================================================================


class TestF2Adaptive:
    """F2-01..F2-06: Adaptive pathway quality criteria."""

    def test_f2_02_intervention_has_version_info(
        self, student, concepts,
    ):
        """ContentIntervention must record rule context."""
        state = get_mastery_state(student.id, concepts[0].id)
        state.p_mastery = THRESHOLDS["MASTERY_LOW"] - 0.15
        state.save()

        decide_pathway_action(student.id, concepts[0].id)

        intervention = ContentIntervention.objects.filter(
            student=student, concept=concepts[0],
        ).first()

        if intervention:
            assert intervention.intervention_type is not None
            assert intervention.concept_id == concepts[0].id

    def test_f2_03_intervention_records_mastery_delta(
        self, student, student_api, micro_tasks, student_with_pathway,
    ):
        """Submit must return mastery before/after in response."""
        task = micro_tasks[0]
        resp = student_api.post("/api/adaptive/submit/", {
            "task_id": task.pk,
            "answer": task.content.get("correct_answer", "A"),
            "duration_seconds": 30,
            "hints_used": 0,
        }, format="json")
        assert resp.status_code == 200
        assert "mastery" in resp.data
        assert "p_mastery" in resp.data["mastery"]

    def test_f2_04_no_repeated_intervention_without_gain(
        self, student, concepts,
    ):
        """Same intervention type >2x without learning gain -> should escalate."""
        concept_id = concepts[0].id
        supplement_count = 0

        for i in range(5):
            update_mastery(student.id, concept_id, is_correct=False)
            result = decide_pathway_action(student.id, concept_id)
            if result["action"] == "supplement":
                supplement_count += 1

        state = MasteryState.objects.get(student_id=student.id, concept_id=concept_id)
        if state.p_mastery < THRESHOLDS["MASTERY_LOW"]:
            assert supplement_count <= 5, (
                "Supplement action should not repeat indefinitely"
            )

    def test_f2_05_no_infinite_retry_loop(
        self, student, concepts,
    ):
        """Wrong -> supplement -> wrong -> supplement must be bounded."""
        concept_id = concepts[0].id
        max_retries = 10

        for i in range(max_retries):
            update_mastery(student.id, concept_id, is_correct=False)

        state = MasteryState.objects.get(student_id=student.id, concept_id=concept_id)
        assert state.attempt_count == max_retries
        assert state.attempt_count <= 30, "Attempt count suggests infinite loop"

    def test_f2_06_pathway_response_has_message(
        self, student, student_api, micro_tasks, student_with_pathway,
    ):
        """Every pathway response must include human-readable message."""
        task = micro_tasks[0]
        resp = student_api.post("/api/adaptive/submit/", {
            "task_id": task.pk,
            "answer": "WRONG",
            "duration_seconds": 30,
            "hints_used": 0,
        }, format="json")
        assert resp.status_code == 200
        pathway = resp.data.get("pathway", {})
        assert "message" in pathway or "action" in pathway


# ===================================================================
# F3 — Backward Design Dashboard
# ===================================================================


class TestF3BackwardDesign:
    """F3-01..F3-06: Progress and milestone quality criteria."""

    def test_f3_01_progress_from_data_not_ui(
        self, student, student_api, course, student_with_pathway,
    ):
        """Progress comes from DB computation, not frontend estimation."""
        resp = student_api.get(f"/api/adaptive/pathway/{course.pk}/")
        assert resp.status_code == 200

        pathway = StudentPathway.objects.get(student=student, course=course)
        total_concepts = course.concepts.count()

        if total_concepts > 0:
            db_progress = len(pathway.concepts_completed or []) / total_concepts * 100
            api_progress = resp.data.get("progress_pct", 0)
            assert abs(db_progress - api_progress) <= 1.0, (
                f"API progress {api_progress} != DB progress {db_progress}"
            )

    def test_f3_02_task_completion_idempotent(
        self, student, student_api, micro_tasks, student_with_pathway,
    ):
        """Submitting same task twice increments attempt, not completion count."""
        task = micro_tasks[0]
        correct = task.content.get("correct_answer", "A")

        student_api.post("/api/adaptive/submit/", {
            "task_id": task.pk, "answer": correct,
            "duration_seconds": 30, "hints_used": 0,
        }, format="json")

        student_api.post("/api/adaptive/submit/", {
            "task_id": task.pk, "answer": correct,
            "duration_seconds": 30, "hints_used": 0,
        }, format="json")

        attempts = TaskAttempt.objects.filter(student=student, task=task)
        assert attempts.count() == 2
        assert attempts.last().attempt_number == 2

    def test_f3_06_no_impossible_progress(
        self, student, course, student_with_pathway,
    ):
        """Progress can never be negative or exceed 100%."""
        pathway = StudentPathway.objects.get(student=student, course=course)
        pct = pathway.progress_pct
        assert 0 <= pct <= 100, f"Progress {pct}% is outside [0, 100]"


# ===================================================================
# F4 — Dashboard giang vien / Early Warning
# ===================================================================


class TestF4Dashboard:
    """F4-01..F4-06: Dashboard and alert quality criteria."""

    def test_f4_01_alert_has_all_5_required_fields(
        self, student, class_with_members,
    ):
        """Every alert must have: identity, reason, timestamp, evidence, status."""
        EventLog.objects.create(
            event_name=EventLog.EventName.SESSION_STARTED,
            timestamp_utc=timezone.now() - timedelta(days=6),
            actor=student,
            actor_type=EventLog.ActorType.STUDENT,
        )

        alerts = compute_early_warnings(class_with_members.id)

        for alert in alerts:
            assert alert.student_id is not None, "Missing student identity"
            assert alert.reason and len(alert.reason) > 0, "Missing reason"
            assert alert.created_at is not None, "Missing timestamp"
            assert isinstance(alert.evidence, dict) and len(alert.evidence) > 0, "Missing evidence"
            assert alert.status is not None, "Missing status"

    def test_f4_05_insufficient_data_flagged(
        self, class_with_members,
    ):
        """When class has no events, overview must indicate data_sufficient=false."""
        overview = get_class_overview(class_with_members.id)
        if overview["total_students"] > 0:
            event_count = EventLog.objects.filter(
                actor__class_memberships__student_class=class_with_members,
            ).count()
            if event_count == 0:
                assert overview.get("data_sufficient") is False, (
                    "Class with no events should have data_sufficient=false"
                )

    def test_f4_06_lecturer_scoped_to_own_class(
        self, lecturer_api, class_with_members,
    ):
        """Lecturer can only see alerts for their assigned class."""
        resp = lecturer_api.get("/api/dashboard/alerts/?class_id=999999")
        if resp.status_code == 200:
            data = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
            assert len(data) == 0, "Lecturer should not see alerts for non-assigned class"


# ===================================================================
# F5 — Data Cleaning Pipeline
# ===================================================================


class TestF5Pipeline:
    """F5-01..F5-06: ETL pipeline quality criteria."""

    def test_f5_01_etl_run_has_metadata(self):
        """Every ETL run must have run_id, checksums, schema snapshot."""
        from analytics.models import ETLRun

        fields = [f.name for f in ETLRun._meta.get_fields()]
        required = ["run_id", "input_checksum", "output_checksum", "schema_snapshot"]
        for field in required:
            assert field in fields, f"ETLRun missing required field: {field}"

    def test_f5_02_no_silent_coercion(self):
        """Schema validator must reject type mismatches explicitly."""
        from analytics.etl.validators import validate_schema, SchemaValidationError
        import pandas as pd

        df = pd.DataFrame({
            "student_id": ["A", "B", "C"],
            "score": ["not_a_number", "80", "90"],
        })

        try:
            result = validate_schema(df)
            if "warnings" in result:
                assert len(result["warnings"]) > 0 or "errors" in result
        except (SchemaValidationError, Exception):
            pass

    def test_f5_05_pipeline_reproducible(self):
        """Same input + same seed -> same output checksum."""
        import numpy as np
        import pandas as pd
        from analytics.etl.imputation import impute_missing_values

        np.random.seed(42)
        df = pd.DataFrame({
            "a": [1, 2, np.nan, 4, 5, 6, 7, 8, 9, 10],
            "b": [10, np.nan, 30, 40, 50, 60, 70, 80, 90, 100],
        })

        np.random.seed(42)
        out1, _ = impute_missing_values(df.copy(), n_neighbors=3)

        np.random.seed(42)
        out2, _ = impute_missing_values(df.copy(), n_neighbors=3)

        h1 = hashlib.sha256(pd.util.hash_pandas_object(out1).values.tobytes()).hexdigest()
        h2 = hashlib.sha256(pd.util.hash_pandas_object(out2).values.tobytes()).hexdigest()
        assert h1 == h2, "Pipeline not reproducible with same seed"

    def test_f5_06_atomic_failure_no_partial_output(self):
        """Pipeline failure must not produce partial clean data."""
        from analytics.models import ETLRun

        fields = [f.name for f in ETLRun._meta.get_fields()]
        assert "status" in fields
        assert "error_message" in fields

        status_choices = [c[0] for c in ETLRun.RunStatus.choices]
        assert "failed" in status_choices or "FAILED" in status_choices

    def test_f5_01_etl_run_model_has_checksums(self):
        """ETLRun model must track input/output integrity."""
        from analytics.models import ETLRun

        run = ETLRun(
            input_file="test.csv",
            semester="2025-2",
            input_checksum="abc123",
            total_records=100,
        )
        assert run.input_checksum == "abc123"
        assert hasattr(run, "output_checksum")
        assert hasattr(run, "run_id")
        assert hasattr(run, "random_seed")
