import pytest
from assessment.models import AssessmentSession, LearnerProfile
from adaptive.models import MasteryState, StudentPathway
from wellbeing.models import WellbeingNudge
from events.models import EventLog

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.integration]


class TestCompleteStudentLearningJourney:

    def test_full_journey(
        self, student, student_api, assessment, course, concepts, milestones, micro_tasks,
    ):
        login_resp = self._login(student)
        assert login_resp.status_code == 200
        assert "access" in login_resp.data

        consent_resp = student_api.post(
            "/api/auth/consent/", {"consent_given": True}, format="json",
        )
        assert consent_resp.status_code == 200
        student.refresh_from_db()
        assert student.consent_given is True

        start_resp = student_api.post(f"/api/assessment/{assessment.pk}/start/")
        assert start_resp.status_code == 201
        session_id = start_resp.data["id"]

        for q in assessment.questions.order_by("order"):
            ans_resp = student_api.post(
                f"/api/assessment/sessions/{session_id}/answer/",
                {"question_id": q.id, "answer": "A", "time_taken_seconds": 30},
                format="json",
            )
            assert ans_resp.status_code == 200

        complete_resp = student_api.post(
            f"/api/assessment/sessions/{session_id}/complete/",
        )
        assert complete_resp.status_code == 200
        assert "profile" in complete_resp.data
        assert LearnerProfile.objects.filter(student=student, course=course).exists()

        pathway_resp = student_api.get(f"/api/adaptive/pathway/{course.pk}/")
        assert pathway_resp.status_code == 200
        assert pathway_resp.data["course"] == course.pk

        task = micro_tasks[0]
        correct_answer = task.content["correct_answer"]
        submit_resp = student_api.post("/api/adaptive/submit/", {
            "task_id": task.pk,
            "answer": correct_answer,
            "duration_seconds": 60,
            "hints_used": 0,
        }, format="json")
        assert submit_resp.status_code == 200
        assert submit_resp.data["attempt"]["is_correct"] is True
        assert "mastery" in submit_resp.data
        assert "pathway" in submit_resp.data

        wrong_resp = student_api.post("/api/adaptive/submit/", {
            "task_id": task.pk,
            "answer": "WRONG_ANSWER",
            "duration_seconds": 45,
            "hints_used": 1,
        }, format="json")
        assert wrong_resp.status_code == 200
        assert wrong_resp.data["attempt"]["is_correct"] is False

        wb_resp = student_api.post(
            "/api/wellbeing/check/", {"continuous_minutes": 55}, format="json",
        )
        assert wb_resp.status_code == 200
        assert wb_resp.data["should_nudge"] is True
        assert WellbeingNudge.objects.filter(student=student).exists()

        event_resp = student_api.post("/api/events/track/", {
            "event_name": "page_view",
            "properties": {"page": "/dashboard"},
        }, format="json")
        assert event_resp.status_code == 201

    def _login(self, user):
        from rest_framework.test import APIClient
        client = APIClient()
        return client.post("/api/auth/login/", {
            "username": user.username,
            "password": "Str0ngP@ss!",
        }, format="json")
