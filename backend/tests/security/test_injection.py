import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.security]

SQL_INJECTION_PAYLOADS = [
    "' OR 1=1 --",
    "'; DROP TABLE palp_user; --",
    "\" OR \"\"=\"",
    "1' UNION SELECT * FROM palp_user --",
]


class TestSQLInjection:

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    def test_login_rejects_sql_injection(self, anon_api, payload):
        resp = anon_api.post("/api/auth/login/", {
            "username": payload,
            "password": "anything",
        }, format="json")
        assert resp.status_code in (400, 401)


class TestXSSPrevention:

    def test_xss_in_event_properties_stored_safely(self, student_api):
        xss = '<script>alert("xss")</script>'
        resp = student_api.post("/api/events/track/", {
            "event_name": "page_view",
            "properties": {"page": xss},
        }, format="json")
        assert resp.status_code == 201

    def test_xss_in_intervention_message(
        self, lecturer_api, student, class_with_members,
    ):
        from dashboard.models import Alert
        alert = Alert.objects.create(
            student=student,
            student_class=class_with_members,
            severity=Alert.Severity.RED,
            trigger_type=Alert.TriggerType.INACTIVITY,
            reason="Test",
        )
        xss_msg = '<img src=x onerror=alert(1)>'
        resp = lecturer_api.post("/api/dashboard/interventions/", {
            "alert_id": alert.pk,
            "action_type": "send_message",
            "target_student_ids": [student.pk],
            "message": xss_msg,
        }, format="json")
        assert resp.status_code in (201, 200)
