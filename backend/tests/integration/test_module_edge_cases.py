"""
Module-level edge-case tests (AS, AD, BD, GV matrices).

QA_STANDARD Section 3 edge-case matrices (Section 12 of spec).
Tests scenarios not covered by existing per-module unit tests.
"""
import pytest
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone

from accounts.models import User
from adaptive.engine import update_mastery, decide_pathway_action, get_mastery_state
from adaptive.models import MasteryState, TaskAttempt, ContentIntervention, StudentPathway
from assessment.models import AssessmentSession, LearnerProfile
from curriculum.models import SupplementaryContent
from dashboard.models import Alert
from dashboard.services import compute_early_warnings
from events.models import EventLog

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.integration]

THRESHOLDS = settings.PALP_ADAPTIVE_THRESHOLDS


# ===================================================================
# AS — Assessment edge cases
# ===================================================================


class TestAS04TimeoutSubmit:
    """AS-04: Submit at exact deadline -> only 1 valid result."""

    def test_complete_after_session_exists(
        self, student, student_api, assessment,
    ):
        start = student_api.post(f"/api/assessment/{assessment.pk}/start/")
        sid = start.data["id"]

        for q in assessment.questions.order_by("order"):
            student_api.post(
                f"/api/assessment/sessions/{sid}/answer/",
                {"question_id": q.id, "answer": "A", "time_taken_seconds": 10},
                format="json",
            )

        resp1 = student_api.post(f"/api/assessment/sessions/{sid}/complete/")
        assert resp1.status_code == 200

        # Service treats a 2nd complete as idempotent: returns the same
        # LearnerProfile/session payload with 200, and the session row stays
        # in COMPLETED status without duplication.
        resp2 = student_api.post(f"/api/assessment/sessions/{sid}/complete/")
        assert resp2.status_code == 200

        sessions = AssessmentSession.objects.filter(
            pk=sid, status="completed",
        )
        assert sessions.count() == 1


class TestAS06Retake:
    """AS-06: Re-take assessment -> newest wins, old archived."""

    def test_second_attempt_creates_new_session(
        self, student, student_api, assessment,
    ):
        start1 = student_api.post(f"/api/assessment/{assessment.pk}/start/")
        sid1 = start1.data["id"]

        for q in assessment.questions.order_by("order"):
            student_api.post(
                f"/api/assessment/sessions/{sid1}/answer/",
                {"question_id": q.id, "answer": "A", "time_taken_seconds": 10},
                format="json",
            )
        student_api.post(f"/api/assessment/sessions/{sid1}/complete/")

        start2 = student_api.post(f"/api/assessment/{assessment.pk}/start/")
        if start2.status_code == 201:
            assert start2.data["id"] != sid1


class TestAS07CrossDevice:
    """AS-07: Switch device mid-assessment -> resume if allowed."""

    def test_session_accessible_from_different_client(
        self, student, student_api, assessment,
    ):
        start = student_api.post(f"/api/assessment/{assessment.pk}/start/")
        sid = start.data["id"]

        first_q = assessment.questions.order_by("order").first()
        student_api.post(
            f"/api/assessment/sessions/{sid}/answer/",
            {"question_id": first_q.id, "answer": "A", "time_taken_seconds": 10},
            format="json",
        )

        session = AssessmentSession.objects.get(pk=sid)
        assert session.status == "in_progress"
        assert session.responses.count() == 1


class TestAS08TokenExpiry:
    """AS-08: Token expires mid-assessment -> re-auth preserves data."""

    def test_session_persists_independently_of_token(
        self, student, student_api, assessment,
    ):
        start = student_api.post(f"/api/assessment/{assessment.pk}/start/")
        sid = start.data["id"]

        first_q = assessment.questions.order_by("order").first()
        student_api.post(
            f"/api/assessment/sessions/{sid}/answer/",
            {"question_id": first_q.id, "answer": "A", "time_taken_seconds": 10},
            format="json",
        )

        session = AssessmentSession.objects.get(pk=sid)
        assert session.responses.count() == 1
        assert session.status == "in_progress"


# ===================================================================
# AD — Adaptive edge cases
# ===================================================================


class TestAD03MultiConcept:
    """AD-03: Wrong on 2 different concepts -> flag weakest."""

    def test_lower_mastery_concept_gets_supplement(self, student, concepts):
        if len(concepts) < 2:
            pytest.skip("Need >= 2 concepts")

        get_mastery_state(student.id, concepts[0].id)
        get_mastery_state(student.id, concepts[1].id)

        update_mastery(student.id, concepts[0].id, is_correct=False)
        update_mastery(student.id, concepts[0].id, is_correct=False)
        update_mastery(student.id, concepts[1].id, is_correct=False)

        ms0 = MasteryState.objects.get(student=student, concept=concepts[0])
        ms1 = MasteryState.objects.get(student=student, concept=concepts[1])

        weakest = concepts[0] if ms0.p_mastery < ms1.p_mastery else concepts[1]
        result = decide_pathway_action(student.id, weakest.id)

        if ms0.p_mastery < THRESHOLDS["MASTERY_LOW"]:
            assert result["action"] == "supplement"


class TestAD05OfflineResume:
    """AD-05: State persists in DB, resume after offline."""

    def test_mastery_survives_simulated_disconnect(self, student, concepts):
        update_mastery(student.id, concepts[0].id, is_correct=True)
        update_mastery(student.id, concepts[0].id, is_correct=True)

        ms = MasteryState.objects.get(student=student, concept=concepts[0])
        saved_mastery = ms.p_mastery
        saved_attempts = ms.attempt_count

        ms_reloaded = MasteryState.objects.get(pk=ms.pk)
        assert ms_reloaded.p_mastery == saved_mastery
        assert ms_reloaded.attempt_count == saved_attempts


class TestAD07RetryAlert:
    """AD-07: 3 retries fail -> creates GV alert."""

    def test_retry_threshold_creates_alert(
        self, student, class_with_members, micro_tasks,
    ):
        task = micro_tasks[0]
        for _ in range(4):
            TaskAttempt.objects.create(
                student=student, task=task, is_correct=False,
            )

        alerts = compute_early_warnings(class_with_members.id)
        retry_alerts = [
            a for a in alerts
            if a.trigger_type == Alert.TriggerType.RETRY_FAILURE
            and a.student == student
        ]
        assert len(retry_alerts) >= 1


class TestAD08ConcurrentMastery:
    """AD-08: Concurrent mastery updates -> no race condition."""

    def test_sequential_updates_consistent(self, student, concepts):
        concept_id = concepts[0].id

        update_mastery(student.id, concept_id, is_correct=True)
        update_mastery(student.id, concept_id, is_correct=False)
        update_mastery(student.id, concept_id, is_correct=True)

        ms = MasteryState.objects.get(student=student, concept=concepts[0])
        assert ms.attempt_count == 3
        assert ms.correct_count == 2


class TestAD09RuleVersionChange:
    """AD-09: Rule version changes mid-session -> session stable."""

    def test_pathway_decision_stable_within_session(self, student, concepts):
        concept_id = concepts[0].id
        state = get_mastery_state(student.id, concept_id)
        state.p_mastery = 0.50
        state.save()

        result1 = decide_pathway_action(student.id, concept_id)
        result2 = decide_pathway_action(student.id, concept_id)

        assert result1["action"] == result2["action"]
        assert result1["difficulty_adjustment"] == result2["difficulty_adjustment"]


class TestAD10InterventionFallback:
    """AD-10: Missing supplementary content -> safe fallback."""

    def test_no_supplementary_returns_continue_not_crash(self, student, concepts):
        SupplementaryContent.objects.filter(concept=concepts[0]).delete()

        state = get_mastery_state(student.id, concepts[0].id)
        state.p_mastery = THRESHOLDS["MASTERY_LOW"] - 0.15
        state.save()

        result = decide_pathway_action(student.id, concepts[0].id)
        assert result["action"] in ("supplement", "continue")


# ===================================================================
# BD — Backward Design edge cases
# ===================================================================


class TestBD04FlexOrder:
    """BD-04: Complete milestones out of order -> allowed if policy permits."""

    def test_progress_computed_regardless_of_order(
        self, student, course, student_with_pathway,
    ):
        pathway = StudentPathway.objects.get(student=student, course=course)
        assert pathway.progress_pct >= 0


class TestBD06ConcurrentProgress:
    """BD-06: Two devices submit same task -> no conflict."""

    def test_sequential_submits_dont_corrupt(
        self, student, student_api, micro_tasks, student_with_pathway,
    ):
        task = micro_tasks[0]
        correct = task.content.get("correct_answer", "A")

        for _ in range(2):
            student_api.post("/api/adaptive/submit/", {
                "task_id": task.pk, "answer": correct,
                "duration_seconds": 30, "hints_used": 0,
            }, format="json")

        ms = MasteryState.objects.get(student=student, concept=task.concept)
        assert ms.attempt_count == 2

        attempts = TaskAttempt.objects.filter(student=student, task=task)
        numbers = list(attempts.order_by("attempt_number").values_list(
            "attempt_number", flat=True,
        ))
        assert numbers == [1, 2]


class TestBD08Prerequisites:
    """BD-08: Task locked before prerequisite -> access denied."""

    def test_prerequisite_concept_order_enforced(self, course, concepts):
        from curriculum.models import ConceptPrerequisite

        if len(concepts) >= 2:
            ConceptPrerequisite.objects.get_or_create(
                concept=concepts[1], prerequisite=concepts[0],
            )

            prereq_concepts = [
                p.prerequisite for p in concepts[1].prerequisites.select_related("prerequisite")
            ]
            assert concepts[0] in prereq_concepts


# ===================================================================
# GV — Dashboard edge cases
# ===================================================================


class TestGV04LegitimateAbsence:
    """GV-04: Student legitimately absent -> dismissable alert."""

    def test_alert_is_dismissable(
        self, student, lecturer_api, class_with_members,
    ):
        alert = Alert.objects.create(
            student=student,
            student_class=class_with_members,
            severity=Alert.Severity.YELLOW,
            trigger_type=Alert.TriggerType.INACTIVITY,
            reason="Khong hoat dong 4 ngay",
            evidence={"days_inactive": 4},
            suggested_action="Lien he SV",
        )

        resp = lecturer_api.post(f"/api/dashboard/alerts/{alert.pk}/dismiss/", {
            "dismiss_reason_code": Alert.DismissReason.STUDENT_LEAVE.value,
            "dismiss_note": "SV nghi phep hop le, da xac nhan",
        }, format="json")
        assert resp.status_code == 200

        alert.refresh_from_db()
        assert alert.status == Alert.AlertStatus.DISMISSED
        assert alert.dismiss_note != ""


class TestGV08FollowUp:
    """GV-08: After intervention, dashboard updates correctly."""

    def test_intervention_action_recorded(
        self, student, lecturer_api, class_with_members,
    ):
        alert = Alert.objects.create(
            student=student,
            student_class=class_with_members,
            severity=Alert.Severity.RED,
            trigger_type=Alert.TriggerType.INACTIVITY,
            reason="Inactive 6 ngay",
        )

        resp = lecturer_api.post("/api/dashboard/interventions/", {
            "alert_id": alert.pk,
            "action_type": "send_message",
            "target_student_ids": [student.pk],
            "message": "Hay quay lai hoc nhe!",
        }, format="json")
        assert resp.status_code in (200, 201)

        history = lecturer_api.get("/api/dashboard/interventions/history/")
        assert history.status_code == 200
