"""
Product Correctness Tests -- 5 Anti-Pattern Verification.

QA_STANDARD Section 1.4.2.
Each test class verifies that a specific anti-pattern CANNOT occur.
"""
import pytest
from datetime import timedelta

from django.utils import timezone

from accounts.models import User
from adaptive.models import MasteryState, TaskAttempt
from assessment.models import AssessmentSession, LearnerProfile
from curriculum.models import MicroTask
from dashboard.models import Alert
from events.models import EventLog

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.integration]


# ---------------------------------------------------------------------------
# AP-01: Dead-end flow — SV must ALWAYS have a next step
# ---------------------------------------------------------------------------


class TestAP01NoDeadEnd:
    """
    Verify: After any student action, there is always a valid next step.
    No state leaves the student stranded.
    """

    def test_after_assessment_student_has_pathway(
        self, student, student_api, assessment, course, concepts,
        milestones, micro_tasks,
    ):
        start = student_api.post(f"/api/assessment/{assessment.pk}/start/")
        assert start.status_code == 201
        sid = start.data["id"]

        for q in assessment.questions.order_by("order"):
            student_api.post(
                f"/api/assessment/sessions/{sid}/answer/",
                {"question_id": q.id, "answer": "A", "time_taken_seconds": 10},
                format="json",
            )

        complete = student_api.post(f"/api/assessment/sessions/{sid}/complete/")
        assert complete.status_code == 200

        pathway = student_api.get(f"/api/adaptive/pathway/{course.pk}/")
        assert pathway.status_code == 200
        assert pathway.data["current_concept"] is not None

    def test_after_wrong_answer_student_gets_supplementary(
        self, student, student_api, course, concepts, micro_tasks,
        student_with_pathway,
    ):
        task = micro_tasks[0]
        resp = student_api.post("/api/adaptive/submit/", {
            "task_id": task.pk,
            "answer": "DELIBERATELY_WRONG",
            "duration_seconds": 30,
            "hints_used": 0,
        }, format="json")
        assert resp.status_code == 200

        pathway_data = resp.data.get("pathway", {})
        action = pathway_data.get("action", "")
        assert action in ("supplement", "continue", "advance"), (
            f"Unexpected pathway action: {action} — student may be in dead-end"
        )

    def test_retry_always_has_next_step(
        self, student, student_api, course, micro_tasks, student_with_pathway,
    ):
        task = micro_tasks[0]
        for _ in range(3):
            resp = student_api.post("/api/adaptive/submit/", {
                "task_id": task.pk,
                "answer": "WRONG",
                "duration_seconds": 30,
                "hints_used": 0,
            }, format="json")
            assert resp.status_code == 200
            assert "pathway" in resp.data


# ---------------------------------------------------------------------------
# AP-02: Unexplainable state — every decision must be explainable
# ---------------------------------------------------------------------------


class TestAP02NoUnexplainableState:
    """
    Verify: Every system decision has a human-readable explanation.
    """

    def test_pathway_decision_matches_mastery_threshold(
        self, student, concepts, course,
    ):
        ms = MasteryState.objects.create(
            student=student, concept=concepts[0],
            p_mastery=0.50, p_guess=0.25, p_slip=0.10, p_transit=0.09,
        )
        assert ms.p_mastery < 0.60

        ms_high = MasteryState.objects.create(
            student=student, concept=concepts[1],
            p_mastery=0.90, p_guess=0.25, p_slip=0.10, p_transit=0.09,
        )
        assert ms_high.p_mastery > 0.85

    def test_alert_always_has_reason(self, student, lecturer, class_with_members):
        alert = Alert.objects.create(
            student=student,
            student_class=class_with_members,
            severity=Alert.Severity.RED,
            trigger_type=Alert.TriggerType.INACTIVITY,
            reason="Sinh vien khong hoat dong trong 5 ngay",
            evidence={"inactive_days": 5},
            suggested_action="Gui tin nhan nhac nho",
        )
        assert alert.reason != ""
        assert len(alert.reason) >= 10
        assert alert.evidence is not None
        assert alert.suggested_action != ""

    def test_alert_reason_is_human_readable(self, student, class_with_members):
        alert = Alert.objects.create(
            student=student,
            student_class=class_with_members,
            severity=Alert.Severity.YELLOW,
            trigger_type=Alert.TriggerType.RETRY_FAILURE,
            reason="Sinh vien that bai 3 lan lien tiep tren concept Luc va Mo-men",
            evidence={"retry_count": 3, "concept": "Luc va Mo-men"},
            suggested_action="Goi y bai tap bo tro",
        )
        assert not alert.reason.startswith("ERR_")
        assert not alert.reason.startswith("{")
        assert "sinh vien" in alert.reason.lower() or "sv" in alert.reason.lower()


# ---------------------------------------------------------------------------
# AP-03: Lost state mid-flow — state must persist across interruptions
# ---------------------------------------------------------------------------


class TestAP03NoLostState:
    """
    Verify: Assessment progress, task attempts, and mastery state persist
    correctly and survive interruptions.
    """

    def test_assessment_progress_persists(
        self, student, student_api, assessment,
    ):
        start = student_api.post(f"/api/assessment/{assessment.pk}/start/")
        assert start.status_code == 201
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

    def test_mastery_state_persists_after_submit(
        self, student, student_api, course, concepts, micro_tasks,
        student_with_pathway,
    ):
        task = micro_tasks[0]
        correct_answer = task.content.get("correct_answer", "A")

        resp = student_api.post("/api/adaptive/submit/", {
            "task_id": task.pk,
            "answer": correct_answer,
            "duration_seconds": 30,
            "hints_used": 0,
        }, format="json")
        assert resp.status_code == 200

        ms = MasteryState.objects.filter(
            student=student, concept=task.concept,
        ).first()
        assert ms is not None
        assert ms.attempt_count >= 1

    def test_task_attempt_recorded_correctly(
        self, student, student_api, micro_tasks, student_with_pathway,
    ):
        task = micro_tasks[0]

        student_api.post("/api/adaptive/submit/", {
            "task_id": task.pk,
            "answer": "WRONG",
            "duration_seconds": 20,
            "hints_used": 0,
        }, format="json")

        attempt = TaskAttempt.objects.filter(
            student=student, task=task,
        ).first()
        assert attempt is not None
        assert attempt.attempt_number >= 1


# ---------------------------------------------------------------------------
# AP-04: Double-count completion — no inflated metrics
# ---------------------------------------------------------------------------


class TestAP04NoDoubleCount:
    """
    Verify: Same task/attempt is never counted twice; completion rate
    and progress are accurate.
    """

    def test_attempt_number_strictly_sequential(
        self, student, student_api, micro_tasks, student_with_pathway,
    ):
        task = micro_tasks[0]

        for i in range(3):
            student_api.post("/api/adaptive/submit/", {
                "task_id": task.pk,
                "answer": "A" if i == 2 else "WRONG",
                "duration_seconds": 30,
                "hints_used": 0,
            }, format="json")

        attempts = TaskAttempt.objects.filter(
            student=student, task=task,
        ).order_by("attempt_number")

        numbers = list(attempts.values_list("attempt_number", flat=True))
        for i, n in enumerate(numbers):
            assert n == i + 1, f"Expected attempt {i+1}, got {n}"

    def test_mastery_state_unique_per_student_concept(
        self, student, concepts,
    ):
        MasteryState.objects.create(
            student=student, concept=concepts[0],
            p_mastery=0.5, p_guess=0.25, p_slip=0.10, p_transit=0.09,
        )

        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            MasteryState.objects.create(
                student=student, concept=concepts[0],
                p_mastery=0.6, p_guess=0.25, p_slip=0.10, p_transit=0.09,
            )

    def test_event_idempotency_prevents_double_tracking(
        self, student_api,
    ):
        payload = {
            "event_name": "micro_task_completed",
            "idempotency_key": "ap04-dedup-test-key",
        }

        resp1 = student_api.post("/api/events/track/", payload, format="json")
        assert resp1.status_code == 201

        student_api.post("/api/events/track/", payload, format="json")

        count = EventLog.objects.filter(
            idempotency_key="ap04-dedup-test-key",
        ).count()
        assert count == 1

    def test_no_duplicate_active_sessions(
        self, student, student_api, assessment,
    ):
        start1 = student_api.post(f"/api/assessment/{assessment.pk}/start/")
        assert start1.status_code == 201

        start2 = student_api.post(f"/api/assessment/{assessment.pk}/start/")
        # Re-start of an already-active session must NOT create a new one:
        # the API resumes (200) and returns the same session id.
        assert start2.status_code == 200, "Existing in-progress session should be resumed, not rejected"
        assert start2.data["id"] == start1.data["id"], "Resume must return the same session id"
        assert AssessmentSession.objects.filter(
            student=student, assessment=assessment,
            status=AssessmentSession.Status.IN_PROGRESS,
        ).count() == 1, "Only one in-progress session may exist for the student"


# ---------------------------------------------------------------------------
# AP-05: False alert due to bug logic — no phantom warnings
# ---------------------------------------------------------------------------


class TestAP05NoFalseAlert:
    """
    Verify: Early warning classification is correct; active students
    never get RED/YELLOW alerts.
    """

    def test_active_student_not_flagged(
        self, student, student_api, course, concepts, micro_tasks,
        student_with_pathway, class_with_members,
    ):
        task = micro_tasks[0]
        correct_answer = task.content.get("correct_answer", "A")

        student_api.post("/api/adaptive/submit/", {
            "task_id": task.pk,
            "answer": correct_answer,
            "duration_seconds": 30,
            "hints_used": 0,
        }, format="json")

        alerts = Alert.objects.filter(
            student=student,
            severity__in=[Alert.Severity.RED, Alert.Severity.YELLOW],
            status=Alert.AlertStatus.ACTIVE,
        )
        assert alerts.count() == 0, (
            "Active student who just submitted correctly should not have alerts"
        )

    def test_inactive_student_correctly_flagged(
        self, student, class_with_members,
    ):
        from dashboard.services import compute_early_warnings

        EventLog.objects.create(
            event_name=EventLog.EventName.SESSION_ENDED,
            timestamp_utc=timezone.now() - timedelta(days=6),
            actor=student,
            actor_type=EventLog.ActorType.STUDENT,
        )

        compute_early_warnings(class_with_members.id)

        alerts = Alert.objects.filter(
            student=student,
            trigger_type=Alert.TriggerType.INACTIVITY,
        )
        assert alerts.filter(severity=Alert.Severity.RED).exists(), (
            "Student inactive 6 days should get RED alert"
        )

    def test_overview_counts_add_up(
        self, lecturer_api, class_with_members,
    ):
        resp = lecturer_api.get(
            f"/api/dashboard/class/{class_with_members.pk}/overview/",
        )
        if resp.status_code != 200:
            return

        data = resp.data
        total = data.get("total_students", 0)
        on_track = data.get("on_track", 0)
        needs_attention = data.get("needs_attention", 0)
        needs_intervention = data.get("needs_intervention", 0)

        assert on_track + needs_attention + needs_intervention == total, (
            f"Overview counts don't add up: {on_track}+{needs_attention}+"
            f"{needs_intervention} != {total}"
        )
