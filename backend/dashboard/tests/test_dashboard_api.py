import pytest
from rest_framework import status

from dashboard.models import Alert, InterventionAction

pytestmark = pytest.mark.django_db

URL_OVERVIEW = "/api/dashboard/class/{}/overview/"
URL_ALERTS = "/api/dashboard/alerts/"
URL_DISMISS = "/api/dashboard/alerts/{}/dismiss/"
URL_INTERVENTIONS = "/api/dashboard/interventions/"
URL_HISTORY = "/api/dashboard/interventions/history/"


def _make_alert(student, student_class, severity=Alert.Severity.YELLOW,
                trigger=Alert.TriggerType.INACTIVITY):
    return Alert.objects.create(
        student=student,
        student_class=student_class,
        severity=severity,
        trigger_type=trigger,
        reason="Test alert",
    )


class TestClassOverviewAPI:
    def test_lecturer_gets_200_with_correct_data(
        self, lecturer_api, class_with_members
    ):
        resp = lecturer_api.get(URL_OVERVIEW.format(class_with_members.id))

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["total_students"] == 2
        assert "on_track" in resp.data
        assert "needs_attention" in resp.data
        assert "needs_intervention" in resp.data

    def test_student_gets_403(self, student_api, class_with_members):
        resp = student_api.get(URL_OVERVIEW.format(class_with_members.id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_gets_401(self, anon_api, class_with_members):
        resp = anon_api.get(URL_OVERVIEW.format(class_with_members.id))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestAlertListAPI:
    def test_lecturer_gets_200(
        self, lecturer_api, student, class_with_members
    ):
        _make_alert(student, class_with_members)

        resp = lecturer_api.get(
            f"{URL_ALERTS}?class_id={class_with_members.id}"
        )

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] >= 1

    def test_unauthenticated_gets_401(self, anon_api):
        resp = anon_api.get(URL_ALERTS)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestDismissAlertAPI:
    def test_dismiss_sets_status(
        self, lecturer_api, student, class_with_members
    ):
        alert = _make_alert(student, class_with_members)

        resp = lecturer_api.post(
            URL_DISMISS.format(alert.id),
            {"dismiss_note": "Student on leave"},
            format="json",
        )

        assert resp.status_code == status.HTTP_200_OK
        alert.refresh_from_db()
        assert alert.status == Alert.AlertStatus.DISMISSED
        assert alert.dismiss_note == "Student on leave"
        assert alert.resolved_at is not None


class TestCreateInterventionAPI:
    def test_creates_intervention_and_resolves_alert(
        self, lecturer_api, student, class_with_members
    ):
        alert = _make_alert(
            student, class_with_members, severity=Alert.Severity.RED,
            trigger=Alert.TriggerType.RETRY_FAILURE,
        )

        resp = lecturer_api.post(URL_INTERVENTIONS, {
            "alert_id": alert.id,
            "action_type": "send_message",
            "target_student_ids": [student.id],
            "message": "Please retry the exercise",
        }, format="json")

        assert resp.status_code == status.HTTP_201_CREATED
        alert.refresh_from_db()
        assert alert.status == Alert.AlertStatus.RESOLVED
        assert InterventionAction.objects.filter(alert=alert).exists()


class TestInterventionHistoryAPI:
    def test_lecturer_gets_200(
        self, lecturer_api, lecturer, student, class_with_members
    ):
        alert = _make_alert(student, class_with_members)
        InterventionAction.objects.create(
            alert=alert,
            lecturer=lecturer,
            action_type=InterventionAction.ActionType.SEND_MESSAGE,
            message="Check in",
        )

        resp = lecturer_api.get(URL_HISTORY)

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] >= 1

    def test_unauthenticated_gets_401(self, anon_api):
        resp = anon_api.get(URL_HISTORY)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
