import logging
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db.models import Avg, Count, Max, Min
from django.utils import timezone

from accounts.models import User
from adaptive.models import MasteryState, TaskAttempt
from dashboard.models import Alert
from events.models import EventLog
from wellbeing.models import WellbeingNudge
from .models import KPIDefinition, KPILineageLog, PilotReport

logger = logging.getLogger("palp")

KPI_COMPUTE_MAP = {
    "active_learning_time": "_compute_active_learning_time_with_lineage",
    "micro_task_completion": "_compute_completion_rate_with_lineage",
    "csat_score": "_compute_csat_with_lineage",
    "gv_dashboard_usage": "_compute_dashboard_usage_with_lineage",
    "time_to_detect_struggling": "_compute_detection_time_with_lineage",
}

MAX_SESSION_MINUTES = 180
SAMPLE_EVENT_LIMIT = 10
VOLUME_DROP_SUSPICIOUS_RATIO = 0.3


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_kpi_snapshot(class_id: int, week_number: int) -> dict:
    students = User.objects.filter(
        class_memberships__student_class_id=class_id,
        role=User.Role.STUDENT,
    )
    now = timezone.now()
    week_ago = now - timedelta(days=7)

    active_learning = _compute_active_learning_time(students, week_ago, now)
    completion_rate = _compute_completion_rate(students)
    dashboard_usage = _compute_dashboard_usage(class_id, week_ago, now)
    wellbeing_stats = _compute_wellbeing_stats(students, week_ago, now)

    return {
        "week": week_number,
        "timestamp": now.isoformat(),
        "cohort_size": students.count(),
        "active_learning_minutes_per_week": active_learning,
        "micro_task_completion_rate": completion_rate,
        "dashboard_usage_per_week": dashboard_usage,
        "wellbeing": wellbeing_stats,
        "mastery": _compute_mastery_stats(students),
        "alerts": _compute_alert_stats(class_id),
    }


def generate_kpi_snapshot_with_integrity(
    class_id: int, week_number: int, *, report: PilotReport | None = None,
) -> dict:
    students = User.objects.filter(
        class_memberships__student_class_id=class_id,
        role=User.Role.STUDENT,
    )
    now = timezone.now()
    week_ago = now - timedelta(days=7)

    kpi_defs = {d.code: d for d in KPIDefinition.objects.all()}
    period = _resolve_period(now, kpi_defs)

    results = {}
    lineage_entries = []

    for code, kpi_def in kpi_defs.items():
        fn_name = KPI_COMPUTE_MAP.get(code)
        if fn_name is None:
            continue
        compute_fn = globals().get(fn_name)
        if compute_fn is None:
            continue

        result = compute_fn(
            students=students, class_id=class_id,
            start=week_ago, end=now, kpi_def=kpi_def,
        )

        flags = _detect_anomalies(
            kpi_def, result, class_id, week_number, week_ago, now,
        )

        lineage = KPILineageLog(
            kpi=kpi_def,
            report=report,
            week_number=week_number,
            class_id=class_id,
            computed_value=result["value"],
            event_count=result["event_count"],
            event_date_range=result["date_range"],
            sample_event_ids=result["sample_ids"],
            computation_params=result.get("params", {}),
            data_quality_flags=flags,
            definition_version=kpi_def.current_version,
        )
        lineage_entries.append(lineage)
        results[code] = {
            "value": result["value"],
            "event_count": result["event_count"],
            "flags": flags,
            "version": kpi_def.current_version,
        }

    if lineage_entries:
        KPILineageLog.objects.bulk_create(lineage_entries)

    snapshot = generate_kpi_snapshot(class_id, week_number)
    snapshot["integrity"] = {
        "period": period,
        "kpi_details": results,
        "schema_version": KPIDefinition.SCHEMA_VERSION,
    }
    return snapshot


def lock_baseline(kpi_code: str, class_id: int) -> KPIDefinition:
    kpi_def = KPIDefinition.objects.get(code=kpi_code)
    if kpi_def.is_locked:
        raise ValidationError(f"KPI '{kpi_code}' is already locked.")
    if not kpi_def.baseline_period_start or not kpi_def.baseline_period_end:
        raise ValidationError(f"KPI '{kpi_code}' has no baseline period configured.")

    students = User.objects.filter(
        class_memberships__student_class__id=class_id,
        role=User.Role.STUDENT,
    )
    fn_name = KPI_COMPUTE_MAP.get(kpi_code)
    if fn_name is None:
        raise ValidationError(f"No compute function registered for '{kpi_code}'.")

    compute_fn = globals().get(fn_name)
    result = compute_fn(
        students=students, class_id=class_id,
        start=kpi_def.baseline_period_start, end=kpi_def.baseline_period_end,
        kpi_def=kpi_def,
    )

    kpi_def.baseline_value = result["value"]
    kpi_def.baseline_locked_at = timezone.now()
    kpi_def.is_locked = True
    super(KPIDefinition, kpi_def).save(
        update_fields=[
            "baseline_value", "baseline_locked_at", "is_locked", "updated_at",
        ],
    )

    KPILineageLog.objects.create(
        kpi=kpi_def,
        week_number=0,
        class_id=class_id,
        computed_value=result["value"],
        event_count=result["event_count"],
        event_date_range=result["date_range"],
        sample_event_ids=result["sample_ids"],
        computation_params={"purpose": "baseline_lock"},
        data_quality_flags={},
        definition_version=kpi_def.current_version,
    )

    logger.info("Locked baseline for %s = %s", kpi_code, result["value"])
    return kpi_def


def generate_pilot_report(
    class_id: int, week_number: int, report_type: str = "weekly",
) -> PilotReport:
    kpi_defs = KPIDefinition.objects.all()
    defs_snapshot = {d.code: d.snapshot_dict() for d in kpi_defs}

    report = PilotReport(
        title=f"Báo cáo tuần {week_number}",
        report_type=report_type,
        week_number=week_number,
        schema_version=KPIDefinition.SCHEMA_VERSION,
        kpi_definitions_snapshot=defs_snapshot,
    )
    report.save()

    snapshot = generate_kpi_snapshot_with_integrity(
        class_id, week_number, report=report,
    )

    report.kpi_data = snapshot
    report.usage_data = {
        "active_learning": snapshot["active_learning_minutes_per_week"],
        "completion": snapshot["micro_task_completion_rate"],
        "dashboard_usage": snapshot["dashboard_usage_per_week"],
    }
    report.save(update_fields=["kpi_data", "usage_data"])

    logger.info("Generated pilot report: %s", report.title)
    return report


# ---------------------------------------------------------------------------
# Lineage-aware compute functions
# ---------------------------------------------------------------------------


def _compute_active_learning_time_with_lineage(
    *, students, class_id, start, end, kpi_def,
) -> dict:
    events = EventLog.objects.filter(
        actor__in=students,
        event_name__in=[
            EventLog.EventName.SESSION_STARTED,
            EventLog.EventName.SESSION_ENDED,
        ],
        timestamp_utc__range=(start, end),
    ).order_by("actor", "timestamp_utc")

    event_ids = list(events.values_list("id", flat=True)[:SAMPLE_EVENT_LIMIT])
    date_range = events.aggregate(first=Min("timestamp_utc"), last=Max("timestamp_utc"))

    total_minutes = 0
    for student in students:
        user_sessions = events.filter(actor=student)
        starts = user_sessions.filter(event_name=EventLog.EventName.SESSION_STARTED)
        for s in starts:
            end_event = user_sessions.filter(
                event_name=EventLog.EventName.SESSION_ENDED,
                timestamp_utc__gt=s.timestamp_utc,
            ).first()
            if end_event:
                duration = (end_event.timestamp_utc - s.timestamp_utc).total_seconds() / 60
                total_minutes += min(duration, MAX_SESSION_MINUTES)

    count = students.count()
    value = round(total_minutes / count, 1) if count > 0 else 0

    return {
        "value": value,
        "event_count": events.count(),
        "sample_ids": event_ids,
        "date_range": {
            "start": date_range["first"].isoformat() if date_range["first"] else None,
            "end": date_range["last"].isoformat() if date_range["last"] else None,
        },
        "params": {"max_session_minutes": MAX_SESSION_MINUTES, "cohort_size": count},
    }


def _compute_completion_rate_with_lineage(
    *, students, class_id, start, end, kpi_def,
) -> dict:
    attempts = TaskAttempt.objects.filter(student__in=students)
    total = attempts.count()
    successful = attempts.filter(is_correct=True).count()
    value = round(successful / total * 100, 1) if total > 0 else 0

    events = EventLog.objects.filter(
        actor__in=students,
        event_name=EventLog.EventName.MICRO_TASK_COMPLETED,
        timestamp_utc__range=(start, end),
    )

    return {
        "value": value,
        "event_count": events.count(),
        "sample_ids": list(events.values_list("id", flat=True)[:SAMPLE_EVENT_LIMIT]),
        "date_range": _event_date_range(events),
        "params": {"total_attempts": total, "successful": successful},
    }


def _compute_csat_with_lineage(*, students, class_id, start, end, kpi_def) -> dict:
    return {
        "value": 0,
        "event_count": 0,
        "sample_ids": [],
        "date_range": {"start": None, "end": None},
        "params": {"source": "external_survey", "manual_entry": True},
    }


def _compute_dashboard_usage_with_lineage(
    *, students, class_id, start, end, kpi_def,
) -> dict:
    events = EventLog.objects.filter(
        actor__class_assignments__student_class_id=class_id,
        event_name=EventLog.EventName.GV_DASHBOARD_VIEWED,
        timestamp_utc__range=(start, end),
    )
    value = events.count()

    return {
        "value": value,
        "event_count": value,
        "sample_ids": list(events.values_list("id", flat=True)[:SAMPLE_EVENT_LIMIT]),
        "date_range": _event_date_range(events),
        "params": {"class_id": class_id},
    }


def _compute_detection_time_with_lineage(
    *, students, class_id, start, end, kpi_def,
) -> dict:
    alerts = Alert.objects.filter(
        student_class_id=class_id,
        created_at__range=(start, end),
    )
    if not alerts.exists():
        return {
            "value": 0,
            "event_count": 0,
            "sample_ids": [],
            "date_range": {"start": None, "end": None},
            "params": {"alert_count": 0},
        }

    total_hours = 0
    count = 0
    for alert in alerts:
        last_event = EventLog.objects.filter(
            actor=alert.student,
            timestamp_utc__lt=alert.created_at,
        ).order_by("-timestamp_utc").first()
        if last_event:
            delta = (alert.created_at - last_event.timestamp_utc).total_seconds() / 3600
            total_hours += delta
            count += 1

    avg_hours = round(total_hours / count, 1) if count > 0 else 0

    return {
        "value": avg_hours,
        "event_count": count,
        "sample_ids": list(alerts.values_list("id", flat=True)[:SAMPLE_EVENT_LIMIT]),
        "date_range": _event_date_range_from_qs(alerts, "created_at"),
        "params": {"alert_count": alerts.count(), "avg_detection_hours": avg_hours},
    }


# ---------------------------------------------------------------------------
# Legacy compute functions (backward-compatible)
# ---------------------------------------------------------------------------


def _compute_active_learning_time(students, start, end):
    sessions = EventLog.objects.filter(
        actor__in=students,
        event_name__in=[
            EventLog.EventName.SESSION_STARTED,
            EventLog.EventName.SESSION_ENDED,
        ],
        timestamp_utc__range=(start, end),
    ).order_by("actor", "timestamp_utc")

    total_minutes = 0
    for student in students:
        user_sessions = sessions.filter(actor=student)
        starts = user_sessions.filter(event_name=EventLog.EventName.SESSION_STARTED)
        for s in starts:
            end_event = user_sessions.filter(
                event_name=EventLog.EventName.SESSION_ENDED,
                timestamp_utc__gt=s.timestamp_utc,
            ).first()
            if end_event:
                duration = (end_event.timestamp_utc - s.timestamp_utc).total_seconds() / 60
                total_minutes += min(duration, MAX_SESSION_MINUTES)

    count = students.count()
    return round(total_minutes / count, 1) if count > 0 else 0


def _compute_completion_rate(students):
    total_attempts = TaskAttempt.objects.filter(student__in=students).count()
    successful = TaskAttempt.objects.filter(student__in=students, is_correct=True).count()
    return round(successful / total_attempts * 100, 1) if total_attempts > 0 else 0


def _compute_dashboard_usage(class_id, start, end):
    return EventLog.objects.filter(
        actor__class_assignments__student_class_id=class_id,
        event_name=EventLog.EventName.GV_DASHBOARD_VIEWED,
        timestamp_utc__range=(start, end),
    ).count()


def _compute_wellbeing_stats(students, start, end):
    nudges = WellbeingNudge.objects.filter(
        student__in=students, created_at__range=(start, end),
    )
    total = nudges.count()
    accepted = nudges.filter(response=WellbeingNudge.NudgeResponse.ACCEPTED).count()
    return {
        "total_nudges": total,
        "accepted": accepted,
        "acceptance_rate": round(accepted / total * 100, 1) if total > 0 else 0,
    }


def _compute_mastery_stats(students):
    stats = MasteryState.objects.filter(student__in=students).aggregate(
        avg=Avg("p_mastery"),
        count=Count("id"),
    )
    return {
        "avg_mastery": round(stats["avg"] or 0, 3),
        "total_records": stats["count"],
    }


def _compute_alert_stats(class_id):
    alerts = Alert.objects.filter(student_class_id=class_id)
    return {
        "total": alerts.count(),
        "active": alerts.filter(status=Alert.AlertStatus.ACTIVE).count(),
        "resolved": alerts.filter(status=Alert.AlertStatus.RESOLVED).count(),
        "dismissed": alerts.filter(status=Alert.AlertStatus.DISMISSED).count(),
    }


# ---------------------------------------------------------------------------
# Integrity helpers
# ---------------------------------------------------------------------------


def _resolve_period(now, kpi_defs: dict) -> str:
    for kpi_def in kpi_defs.values():
        if kpi_def.baseline_period_start and kpi_def.baseline_period_end:
            if kpi_def.baseline_period_start <= now <= kpi_def.baseline_period_end:
                return "baseline"
        if kpi_def.intervention_period_start and kpi_def.intervention_period_end:
            if kpi_def.intervention_period_start <= now <= kpi_def.intervention_period_end:
                return "intervention"
    return "unknown"


def _detect_anomalies(kpi_def, result, class_id, week_number, start, end):
    flags = {}

    if result["event_count"] == 0 and kpi_def.code != "csat_score":
        flags["no_raw_data"] = True

    if week_number > 1:
        prev = KPILineageLog.objects.filter(
            kpi=kpi_def, class_id=class_id, week_number=week_number - 1,
        ).first()
        if prev:
            if prev.definition_version != kpi_def.current_version:
                flags["definition_changed_since_last_week"] = {
                    "previous_version": prev.definition_version,
                    "current_version": kpi_def.current_version,
                }

            prev_events = prev.event_count
            curr_events = result["event_count"]
            if prev_events > 0 and curr_events > 0:
                volume_change = (curr_events - prev_events) / prev_events

                value_improved = _value_improved(
                    kpi_def, prev.computed_value, result["value"],
                )
                if (
                    value_improved
                    and volume_change < -VOLUME_DROP_SUSPICIOUS_RATIO
                ):
                    flags["suspicious_improvement"] = {
                        "reason": "KPI improved but event volume dropped significantly",
                        "event_volume_change_pct": round(volume_change * 100, 1),
                        "previous_value": prev.computed_value,
                        "current_value": result["value"],
                    }

    return flags


def _value_improved(kpi_def, old_value, new_value) -> bool:
    if kpi_def.target_direction == KPIDefinition.TargetDirection.INCREASE:
        return new_value > old_value
    if kpi_def.target_direction == KPIDefinition.TargetDirection.DECREASE:
        return new_value < old_value
    return abs(new_value - kpi_def.target_value) < abs(old_value - kpi_def.target_value)


def _event_date_range(events_qs) -> dict:
    agg = events_qs.aggregate(first=Min("timestamp_utc"), last=Max("timestamp_utc"))
    return {
        "start": agg["first"].isoformat() if agg["first"] else None,
        "end": agg["last"].isoformat() if agg["last"] else None,
    }


def _event_date_range_from_qs(qs, field) -> dict:
    agg = qs.aggregate(first=Min(field), last=Max(field))
    return {
        "start": agg["first"].isoformat() if agg["first"] else None,
        "end": agg["last"].isoformat() if agg["last"] else None,
    }
