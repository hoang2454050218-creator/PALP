"""
Dashboard GV edge-case test matrix (GV-01 .. GV-10).

Covers: empty class data, bulk inactivity alerts, mastery drop flagging,
student leave dismissal, cross-class access denial, dismiss audit trail,
intervention action logging, post-intervention re-measurement,
duplicate alert prevention, and data staleness indicator.
"""
import uuid

import pytest
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import status as http_status


def _idem():
    return {"HTTP_IDEMPOTENCY_KEY": str(uuid.uuid4())}

from accounts.models import (
    ClassMembership,
    LecturerClassAssignment,
    StudentClass,
    User,
)
from adaptive.models import MasteryState, StudentPathway, TaskAttempt
from dashboard.models import Alert, InterventionAction
from dashboard.services import compute_early_warnings, get_class_overview
from events.models import EventLog

pytestmark = pytest.mark.django_db

WARNING = settings.PALP_EARLY_WARNING
URL_OVERVIEW = "/api/dashboard/class/{}/overview/"
URL_ALERTS = "/api/dashboard/alerts/"
URL_DISMISS = "/api/dashboard/alerts/{}/dismiss/"
URL_INTERVENTIONS = "/api/dashboard/interventions/"


def _event(student, days_ago=0):
    EventLog.objects.create(
        actor=student,
        actor_type=EventLog.ActorType.STUDENT,
        event_name=EventLog.EventName.SESSION_STARTED,
        timestamp_utc=timezone.now() - timedelta(days=days_ago),
    )


def _make_alert(student, student_class, severity=Alert.Severity.YELLOW,
                trigger=Alert.TriggerType.INACTIVITY):
    return Alert.objects.create(
        student=student,
        student_class=student_class,
        severity=severity,
        trigger_type=trigger,
        reason="Test alert",
        evidence={"test": True},
        suggested_action="Test action",
    )


# =========================================================================
# GV-01  New class, no data -> data_sufficient = False
# =========================================================================


class TestGV01EmptyClassData:
    def test_overview_shows_data_insufficient(self, class_with_members):
        overview = get_class_overview(class_with_members.id)
        assert overview["data_sufficient"] is False
        assert overview["total_students"] == 2

    def test_api_returns_data_sufficient_field(
        self, lecturer_api, class_with_members,
    ):
        resp = lecturer_api.get(URL_OVERVIEW.format(class_with_members.id))
        assert resp.status_code == http_status.HTTP_200_OK
        assert "data_sufficient" in resp.data
        assert resp.data["data_sufficient"] is False


# =========================================================================
# GV-02  5 SV inactive 3 days -> generate alerts
# =========================================================================


class TestGV02BulkInactivityAlerts:
    def test_five_inactive_students_get_alerts(
        self, bulk_students, student_class, lecturer,
    ):
        LecturerClassAssignment.objects.get_or_create(
            lecturer=lecturer, student_class=student_class,
        )

        for sv in bulk_students:
            _event(sv, days_ago=4)

        alerts = compute_early_warnings(student_class.id)
        inactivity_alerts = [
            a for a in alerts if a.trigger_type == Alert.TriggerType.INACTIVITY
        ]
        assert len(inactivity_alerts) == 5
        assert all(a.severity == Alert.Severity.YELLOW for a in inactivity_alerts)

    def test_mixed_severity_by_days(
        self, student, student_b, class_with_members,
    ):
        _event(student, days_ago=4)
        _event(student_b, days_ago=6)

        alerts = compute_early_warnings(class_with_members.id)
        by_student = {a.student_id: a for a in alerts
                      if a.trigger_type == Alert.TriggerType.INACTIVITY}

        assert by_student[student.id].severity == Alert.Severity.YELLOW
        assert by_student[student_b.id].severity == Alert.Severity.RED


# =========================================================================
# GV-03  Mastery drops sharply -> flag correctly
# =========================================================================


class TestGV03MasteryDropFlag:
    def test_low_mastery_after_many_attempts_creates_red(
        self, student, class_with_members, concepts,
    ):
        MasteryState.objects.create(
            student=student,
            concept=concepts[0],
            p_mastery=0.20,
            attempt_count=8,
            correct_count=2,
        )

        alerts = compute_early_warnings(class_with_members.id)
        low_mastery_alerts = [
            a for a in alerts
            if a.student == student
            and a.trigger_type == Alert.TriggerType.LOW_MASTERY
        ]
        assert len(low_mastery_alerts) == 1
        assert low_mastery_alerts[0].severity == Alert.Severity.RED
        assert "concept_id" in low_mastery_alerts[0].evidence

    def test_adequate_mastery_no_alert(
        self, student, class_with_members, concepts,
    ):
        MasteryState.objects.create(
            student=student,
            concept=concepts[0],
            p_mastery=0.70,
            attempt_count=10,
            correct_count=7,
        )

        alerts = compute_early_warnings(class_with_members.id)
        low_alerts = [
            a for a in alerts
            if a.student == student
            and a.trigger_type == Alert.TriggerType.LOW_MASTERY
        ]
        assert len(low_alerts) == 0


# =========================================================================
# GV-04  SV on valid leave -> dismiss with STUDENT_LEAVE
# =========================================================================


class TestGV04StudentLeaveDismiss:
    def test_dismiss_with_student_leave_code(
        self, lecturer_api, student, class_with_members,
    ):
        alert = _make_alert(student, class_with_members, Alert.Severity.RED)

        resp = lecturer_api.post(
            URL_DISMISS.format(alert.id),
            {
                "dismiss_reason_code": Alert.DismissReason.STUDENT_LEAVE,
                "dismiss_note": "SV nghỉ phép theo đơn",
            },
            format="json",
        )
        assert resp.status_code == http_status.HTTP_200_OK

        alert.refresh_from_db()
        assert alert.status == Alert.AlertStatus.DISMISSED
        assert alert.dismiss_reason_code == Alert.DismissReason.STUDENT_LEAVE
        assert alert.dismiss_note == "SV nghỉ phép theo đơn"
        assert alert.dismissed_by is not None
        assert alert.resolved_at is not None

    def test_false_positive_dismiss(
        self, lecturer_api, student, class_with_members,
    ):
        alert = _make_alert(student, class_with_members)
        resp = lecturer_api.post(
            URL_DISMISS.format(alert.id),
            {
                "dismiss_reason_code": Alert.DismissReason.FALSE_POSITIVE,
                "dismiss_note": "Dữ liệu cũ, SV vẫn hoạt động",
            },
            format="json",
        )
        assert resp.status_code == http_status.HTTP_200_OK
        alert.refresh_from_db()
        assert alert.dismiss_reason_code == Alert.DismissReason.FALSE_POSITIVE


# =========================================================================
# GV-05  GV opens other class -> blocked
# =========================================================================


class TestGV05CrossClassBlocked:
    def test_unassigned_lecturer_gets_403(
        self, lecturer_other_api, class_with_members,
    ):
        resp = lecturer_other_api.get(
            URL_OVERVIEW.format(class_with_members.id)
        )
        assert resp.status_code == http_status.HTTP_403_FORBIDDEN

    def test_unassigned_lecturer_cannot_list_alerts(
        self, lecturer_other_api, student, class_with_members,
    ):
        _make_alert(student, class_with_members)
        resp = lecturer_other_api.get(
            f"{URL_ALERTS}?class_id={class_with_members.id}"
        )
        assert resp.status_code == http_status.HTTP_403_FORBIDDEN

    def test_assigned_lecturer_gets_200(
        self, lecturer_api, class_with_members,
    ):
        resp = lecturer_api.get(URL_OVERVIEW.format(class_with_members.id))
        assert resp.status_code == http_status.HTTP_200_OK

    def test_student_gets_403(self, student_api, class_with_members):
        resp = student_api.get(URL_OVERVIEW.format(class_with_members.id))
        assert resp.status_code == http_status.HTTP_403_FORBIDDEN


# =========================================================================
# GV-06  Dismiss alert -> audit + reason recorded
# =========================================================================


class TestGV06DismissAuditTrail:
    def test_dismiss_populates_all_fields(
        self, lecturer_api, lecturer, student, class_with_members,
    ):
        alert = _make_alert(student, class_with_members, Alert.Severity.RED)

        lecturer_api.post(
            URL_DISMISS.format(alert.id),
            {
                "dismiss_reason_code": Alert.DismissReason.RESOLVED_OFFLINE,
                "dismiss_note": "Đã trao đổi trực tiếp",
            },
            format="json",
        )

        alert.refresh_from_db()
        assert alert.dismissed_by == lecturer
        assert alert.dismiss_reason_code == Alert.DismissReason.RESOLVED_OFFLINE
        assert alert.dismiss_note == "Đã trao đổi trực tiếp"
        assert alert.resolved_at is not None
        assert alert.status == Alert.AlertStatus.DISMISSED

    def test_audit_event_created(
        self, lecturer_api, student, class_with_members,
    ):
        alert = _make_alert(student, class_with_members)
        initial_count = EventLog.objects.count()

        lecturer_api.post(
            URL_DISMISS.format(alert.id),
            {
                "dismiss_reason_code": Alert.DismissReason.OTHER,
                "dismiss_note": "Test",
            },
            format="json",
        )

        assert EventLog.objects.count() > initial_count


# =========================================================================
# GV-07  Send intervention message -> action saved correctly
# =========================================================================


class TestGV07InterventionMessageSaved:
    def test_creates_intervention_with_correct_data(
        self, lecturer_api, lecturer, student, class_with_members,
    ):
        alert = _make_alert(
            student, class_with_members,
            Alert.Severity.RED, Alert.TriggerType.RETRY_FAILURE,
        )

        resp = lecturer_api.post(URL_INTERVENTIONS, {
            "alert_id": alert.id,
            "action_type": "send_message",
            "target_student_ids": [student.id],
            "message": "Hãy thử lại bài tập nhé",
        }, format="json", **_idem())

        assert resp.status_code == http_status.HTTP_201_CREATED

        action = InterventionAction.objects.get(id=resp.data["id"])
        assert action.lecturer == lecturer
        assert action.action_type == InterventionAction.ActionType.SEND_MESSAGE
        assert action.message == "Hãy thử lại bài tập nhé"
        assert student in action.targets.all()

    def test_alert_resolved_after_intervention(
        self, lecturer_api, student, class_with_members,
    ):
        alert = _make_alert(student, class_with_members, Alert.Severity.RED)

        lecturer_api.post(URL_INTERVENTIONS, {
            "alert_id": alert.id,
            "action_type": "suggest_task",
            "target_student_ids": [student.id],
            "message": "Thử bài tập bổ trợ",
        }, format="json", **_idem())

        alert.refresh_from_db()
        assert alert.status == Alert.AlertStatus.RESOLVED

    def test_audit_event_for_intervention(
        self, lecturer_api, student, class_with_members,
    ):
        alert = _make_alert(student, class_with_members)
        initial_count = EventLog.objects.count()

        lecturer_api.post(URL_INTERVENTIONS, {
            "alert_id": alert.id,
            "action_type": "schedule_meeting",
            "target_student_ids": [student.id],
        }, format="json", **_idem())

        assert EventLog.objects.count() > initial_count


# =========================================================================
# GV-08  Action done, re-measure after data change -> dashboard updates
# =========================================================================


class TestGV08PostInterventionReMeasure:
    def test_overview_updates_after_alert_resolved(
        self, student, student_b, class_with_members,
    ):
        _make_alert(
            student, class_with_members,
            Alert.Severity.RED, Alert.TriggerType.INACTIVITY,
        )
        overview_before = get_class_overview(class_with_members.id)
        assert overview_before["needs_intervention"] == 1

        Alert.objects.filter(student=student).update(
            status=Alert.AlertStatus.RESOLVED,
            resolved_at=timezone.now(),
        )

        overview_after = get_class_overview(class_with_members.id)
        assert overview_after["needs_intervention"] == 0
        assert overview_after["on_track"] > overview_before["on_track"]

    def test_new_activity_reflected_in_overview(
        self, student, class_with_members,
    ):
        overview_before = get_class_overview(class_with_members.id)
        events_before = overview_before["data_sufficient"]

        min_events = WARNING.get("MIN_EVENTS_PER_STUDENT", 5)
        total = overview_before["total_students"]
        for _ in range(min_events * total + 1):
            _event(student, days_ago=0)

        overview_after = get_class_overview(class_with_members.id)
        assert overview_after["data_sufficient"] is True


# =========================================================================
# GV-09  Alert job runs again -> no duplicate alerts
# =========================================================================


class TestGV09NoDuplicateAlerts:
    def test_same_conditions_no_new_alerts(
        self, student, class_with_members,
    ):
        _event(student, days_ago=6)

        first_run = compute_early_warnings(class_with_members.id)
        count_after_first = Alert.objects.filter(
            student=student, trigger_type=Alert.TriggerType.INACTIVITY,
        ).count()

        second_run = compute_early_warnings(class_with_members.id)
        count_after_second = Alert.objects.filter(
            student=student, trigger_type=Alert.TriggerType.INACTIVITY,
        ).count()

        assert count_after_first == count_after_second

    def test_retry_failure_not_duplicated(
        self, student, class_with_members, micro_tasks,
    ):
        for i in range(4):
            TaskAttempt.objects.create(
                student=student, task=micro_tasks[0],
                is_correct=False, score=0, max_score=100,
                answer="wrong", attempt_number=i + 1,
            )

        compute_early_warnings(class_with_members.id)
        first_count = Alert.objects.filter(
            student=student, trigger_type=Alert.TriggerType.RETRY_FAILURE,
        ).count()

        compute_early_warnings(class_with_members.id)
        second_count = Alert.objects.filter(
            student=student, trigger_type=Alert.TriggerType.RETRY_FAILURE,
        ).count()

        assert first_count == second_count

    def test_low_mastery_not_duplicated(
        self, student, class_with_members, concepts,
    ):
        MasteryState.objects.create(
            student=student, concept=concepts[0],
            p_mastery=0.20, attempt_count=8,
        )

        compute_early_warnings(class_with_members.id)
        compute_early_warnings(class_with_members.id)

        count = Alert.objects.filter(
            student=student,
            trigger_type=Alert.TriggerType.LOW_MASTERY,
            concept=concepts[0],
        ).count()
        assert count == 1


# =========================================================================
# GV-10  Data stale 24h -> overview indicates staleness
# =========================================================================


class TestGV10DataStaleness:
    def test_data_sufficient_false_when_no_events(self, class_with_members):
        overview = get_class_overview(class_with_members.id)
        assert overview["data_sufficient"] is False

    def test_data_sufficient_true_with_enough_events(
        self, student, student_b, class_with_members,
    ):
        min_events = WARNING.get("MIN_EVENTS_PER_STUDENT", 5)
        for sv in [student, student_b]:
            for i in range(min_events):
                _event(sv, days_ago=0)

        overview = get_class_overview(class_with_members.id)
        assert overview["data_sufficient"] is True

    def test_overview_structure_complete(self, class_with_members):
        overview = get_class_overview(class_with_members.id)
        required_keys = {
            "total_students", "on_track", "needs_attention",
            "needs_intervention", "active_alerts", "avg_mastery",
            "avg_completion_pct", "data_sufficient",
        }
        assert required_keys.issubset(set(overview.keys()))
