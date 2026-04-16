import pytest
from rest_framework import status

from wellbeing.models import WellbeingNudge

pytestmark = pytest.mark.django_db

URL_CHECK = "/api/wellbeing/check/"
URL_RESPOND = "/api/wellbeing/nudge/{}/respond/"
URL_MY = "/api/wellbeing/my/"


class TestCheckWellbeing:
    def test_no_nudge_under_limit(self, student_api):
        resp = student_api.post(URL_CHECK, {
            "continuous_minutes": 30,
        }, format="json")

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["should_nudge"] is False
        assert WellbeingNudge.objects.count() == 0

    def test_nudge_over_limit(self, student_api):
        resp = student_api.post(URL_CHECK, {
            "continuous_minutes": 55,
        }, format="json")

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["should_nudge"] is True
        assert "nudge" in resp.data
        assert "message" in resp.data
        assert WellbeingNudge.objects.count() == 1

    def test_nudge_at_exact_limit(self, student_api):
        resp = student_api.post(URL_CHECK, {
            "continuous_minutes": 50,
        }, format="json")

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["should_nudge"] is True

    def test_unauthenticated_gets_401(self, anon_api):
        resp = anon_api.post(URL_CHECK, {
            "continuous_minutes": 55,
        }, format="json")

        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestNudgeResponse:
    def test_accept_updates_response(self, student_api, student):
        nudge = WellbeingNudge.objects.create(
            student=student,
            nudge_type=WellbeingNudge.NudgeType.BREAK_REMINDER,
            continuous_minutes=55,
        )

        resp = student_api.post(
            URL_RESPOND.format(nudge.id),
            {"response": "accepted"},
            format="json",
        )

        assert resp.status_code == status.HTTP_200_OK
        nudge.refresh_from_db()
        assert nudge.response == WellbeingNudge.NudgeResponse.ACCEPTED
        assert nudge.responded_at is not None

    def test_dismiss_updates_response(self, student_api, student):
        nudge = WellbeingNudge.objects.create(
            student=student,
            nudge_type=WellbeingNudge.NudgeType.BREAK_REMINDER,
            continuous_minutes=55,
        )

        resp = student_api.post(
            URL_RESPOND.format(nudge.id),
            {"response": "dismissed"},
            format="json",
        )

        assert resp.status_code == status.HTTP_200_OK
        nudge.refresh_from_db()
        assert nudge.response == WellbeingNudge.NudgeResponse.DISMISSED


class TestMyNudges:
    def test_returns_own_nudges(self, student_api, student):
        WellbeingNudge.objects.create(
            student=student,
            nudge_type=WellbeingNudge.NudgeType.BREAK_REMINDER,
            continuous_minutes=55,
        )

        resp = student_api.get(URL_MY)

        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1

    def test_unauthenticated_gets_401(self, anon_api):
        resp = anon_api.get(URL_MY)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_multiple_nudges_ordered(self, student_api, student):
        for mins in [55, 60, 70]:
            WellbeingNudge.objects.create(
                student=student,
                nudge_type=WellbeingNudge.NudgeType.BREAK_REMINDER,
                continuous_minutes=mins,
            )

        resp = student_api.get(URL_MY)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 3


class TestWB004AcceptanceRateTracking:
    """WB-004: Acceptance rate must be trackable for KPI."""

    def test_acceptance_rate_computable(self, student_api, student):
        for response_type in ["accepted", "dismissed", "accepted"]:
            nudge = WellbeingNudge.objects.create(
                student=student,
                nudge_type=WellbeingNudge.NudgeType.BREAK_REMINDER,
                continuous_minutes=55,
            )
            student_api.post(
                URL_RESPOND.format(nudge.id),
                {"response": response_type},
                format="json",
            )

        total = WellbeingNudge.objects.filter(student=student).count()
        accepted = WellbeingNudge.objects.filter(
            student=student,
            response=WellbeingNudge.NudgeResponse.ACCEPTED,
        ).count()
        dismissed = WellbeingNudge.objects.filter(
            student=student,
            response=WellbeingNudge.NudgeResponse.DISMISSED,
        ).count()

        assert total == 3
        assert accepted == 2
        assert dismissed == 1
        rate = accepted / (accepted + dismissed)
        assert rate == pytest.approx(2 / 3, abs=0.01)


class TestWB005NudgeNoFlowBreak:
    """WB-005: Nudge must not block the learning flow."""

    def test_nudge_response_is_optional(self, student_api, student):
        nudge = WellbeingNudge.objects.create(
            student=student,
            nudge_type=WellbeingNudge.NudgeType.BREAK_REMINDER,
            continuous_minutes=55,
        )
        assert nudge.response == WellbeingNudge.NudgeResponse.SHOWN
        assert nudge.responded_at is None


class TestWellbeingEventTracking:
    """Verify wellbeing events fire correctly."""

    def test_check_creates_event(self, student_api):
        from events.models import EventLog

        student_api.post(URL_CHECK, {
            "continuous_minutes": 55,
        }, format="json")

        assert EventLog.objects.filter(
            event_name=EventLog.EventName.WELLBEING_NUDGE,
        ).exists()

    def test_accept_creates_accepted_event(self, student_api, student):
        from events.models import EventLog

        nudge = WellbeingNudge.objects.create(
            student=student,
            nudge_type=WellbeingNudge.NudgeType.BREAK_REMINDER,
            continuous_minutes=55,
        )
        student_api.post(
            URL_RESPOND.format(nudge.id),
            {"response": "accepted"},
            format="json",
        )

        assert EventLog.objects.filter(
            event_name=EventLog.EventName.WELLBEING_NUDGE_ACCEPTED,
        ).exists()

    def test_dismiss_creates_dismissed_event(self, student_api, student):
        from events.models import EventLog

        nudge = WellbeingNudge.objects.create(
            student=student,
            nudge_type=WellbeingNudge.NudgeType.BREAK_REMINDER,
            continuous_minutes=55,
        )
        student_api.post(
            URL_RESPOND.format(nudge.id),
            {"response": "dismissed"},
            format="json",
        )

        assert EventLog.objects.filter(
            event_name=EventLog.EventName.WELLBEING_NUDGE_DISMISSED,
        ).exists()
