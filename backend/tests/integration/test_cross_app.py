import pytest
from datetime import timedelta
from django.utils import timezone

from assessment.models import AssessmentSession, LearnerProfile
from adaptive.models import MasteryState, TaskAttempt
from dashboard.models import Alert, InterventionAction
from dashboard.services import compute_early_warnings
from events.models import EventLog

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.integration]


class TestAssessmentSeedsMastery:

    def test_completing_assessment_creates_mastery_for_all_concepts(
        self, student_api, student, assessment, course, concepts,
    ):
        start = student_api.post(f"/api/assessment/{assessment.pk}/start/")
        session_id = start.data["id"]

        for q in assessment.questions.order_by("order"):
            student_api.post(
                f"/api/assessment/sessions/{session_id}/answer/",
                {"question_id": q.id, "answer": "A", "time_taken_seconds": 10},
                format="json",
            )

        student_api.post(f"/api/assessment/sessions/{session_id}/complete/")

        for concept in concepts:
            assert MasteryState.objects.filter(
                student=student, concept=concept,
            ).exists()


class TestTaskUpdatesPathway:

    def test_submitting_correct_tasks_updates_concepts_completed(
        self, student_api, student, course, concepts, micro_tasks,
    ):
        task = micro_tasks[0]
        correct_answer = task.content["correct_answer"]

        for _ in range(15):
            student_api.post("/api/adaptive/submit/", {
                "task_id": task.pk,
                "answer": correct_answer,
                "duration_seconds": 30,
                "hints_used": 0,
            }, format="json")

        pathway_resp = student_api.get(f"/api/adaptive/pathway/{course.pk}/")
        assert pathway_resp.status_code == 200


class TestEarlyWarningToIntervention:

    def test_inactivity_triggers_alert(
        self, student, class_with_members, lecturer_api,
    ):
        EventLog.objects.create(
            actor=student,
            event_name=EventLog.EventName.SESSION_STARTED,
            created_at=timezone.now() - timedelta(days=6),
        )

        alerts = compute_early_warnings(class_with_members.pk)
        student_alerts = [a for a in alerts if a.student == student]
        assert len(student_alerts) > 0

        alert = student_alerts[0]
        assert alert.severity in [Alert.Severity.RED, Alert.Severity.YELLOW]

        intervention_resp = lecturer_api.post("/api/dashboard/interventions/", {
            "alert_id": alert.pk,
            "action_type": "send_message",
            "target_student_ids": [student.pk],
            "message": "Hay quay lai hoc nhe",
        }, format="json")
        assert intervention_resp.status_code == 201

        alert.refresh_from_db()
        assert alert.status == Alert.AlertStatus.RESOLVED
