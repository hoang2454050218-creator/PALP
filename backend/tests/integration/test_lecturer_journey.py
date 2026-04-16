import pytest
from dashboard.models import Alert, InterventionAction

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.integration]


class TestCompleteLecturerWorkflow:

    def test_full_lecturer_journey(
        self, lecturer_api, student, class_with_members,
    ):
        overview_resp = lecturer_api.get(
            f"/api/dashboard/class/{class_with_members.pk}/overview/",
        )
        assert overview_resp.status_code == 200
        assert overview_resp.data["total_students"] == 2

        alert = Alert.objects.create(
            student=student,
            student_class=class_with_members,
            severity=Alert.Severity.YELLOW,
            trigger_type=Alert.TriggerType.INACTIVITY,
            reason="Khong hoat dong 4 ngay",
        )

        list_resp = lecturer_api.get(
            f"/api/dashboard/alerts/?class_id={class_with_members.pk}",
        )
        assert list_resp.status_code == 200

        dismiss_resp = lecturer_api.post(
            f"/api/dashboard/alerts/{alert.pk}/dismiss/",
            {"dismiss_note": "SV bao nghi om"},
            format="json",
        )
        assert dismiss_resp.status_code == 200
        alert.refresh_from_db()
        assert alert.status == Alert.AlertStatus.DISMISSED

        red_alert = Alert.objects.create(
            student=student,
            student_class=class_with_members,
            severity=Alert.Severity.RED,
            trigger_type=Alert.TriggerType.RETRY_FAILURE,
            reason="That bai 5 lan",
        )

        intervention_resp = lecturer_api.post("/api/dashboard/interventions/", {
            "alert_id": red_alert.pk,
            "action_type": "send_message",
            "target_student_ids": [student.pk],
            "message": "Em thu lai bai tap nay nhe",
        }, format="json")
        assert intervention_resp.status_code == 201

        red_alert.refresh_from_db()
        assert red_alert.status == Alert.AlertStatus.RESOLVED
