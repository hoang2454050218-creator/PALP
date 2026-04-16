import logging
from datetime import timedelta

from django.conf import settings
from django.db.models import Avg, Count, Q, Max
from django.utils import timezone

from accounts.models import User
from adaptive.models import MasteryState, TaskAttempt, StudentPathway
from events.models import EventLog
from .models import Alert

logger = logging.getLogger("palp")

WARNING_CONFIG = settings.PALP_EARLY_WARNING


def compute_early_warnings(class_id: int) -> list[Alert]:
    _expire_stale_alerts(class_id)

    students = User.objects.filter(
        class_memberships__student_class_id=class_id,
        role=User.Role.STUDENT,
    )
    now = timezone.now()
    created_alerts = []

    for student in students:
        alerts = []
        alerts.extend(_check_inactivity(student, class_id, now))
        alerts.extend(_check_retry_failures(student, class_id))
        alerts.extend(_check_milestone_lag(student, class_id))
        alerts.extend(_check_low_mastery(student, class_id))
        created_alerts.extend(alerts)

    try:
        from events.metrics import ALERT_GENERATION_TOTAL
        for alert in created_alerts:
            ALERT_GENERATION_TOTAL.labels(alert_type=alert.trigger_type).inc()
    except (ImportError, AttributeError):
        pass

    logger.info(
        "Early warning: generated %d alerts for class %d",
        len(created_alerts), class_id,
    )
    return created_alerts


def _expire_stale_alerts(class_id):
    now = timezone.now()
    expired_count = Alert.objects.filter(
        student_class_id=class_id,
        status=Alert.AlertStatus.ACTIVE,
        expires_at__isnull=False,
        expires_at__lt=now,
    ).update(status=Alert.AlertStatus.EXPIRED)

    if expired_count:
        logger.info("Expired %d stale alerts for class %d", expired_count, class_id)


def _default_expiry():
    days = WARNING_CONFIG.get("ALERT_EXPIRY_DAYS", 14)
    return timezone.now() + timedelta(days=days)


def _check_inactivity(student, class_id, now):
    last_event = EventLog.objects.filter(
        user=student
    ).aggregate(last=Max("created_at"))["last"]

    if not last_event:
        return []

    days_inactive = (now - last_event).days
    yellow_threshold = WARNING_CONFIG["INACTIVITY_YELLOW_DAYS"]
    red_threshold = WARNING_CONFIG["INACTIVITY_RED_DAYS"]

    if days_inactive < yellow_threshold:
        return []

    existing = Alert.objects.filter(
        student=student,
        trigger_type=Alert.TriggerType.INACTIVITY,
        status=Alert.AlertStatus.ACTIVE,
    ).exists()
    if existing:
        return []

    severity = Alert.Severity.RED if days_inactive >= red_threshold else Alert.Severity.YELLOW
    alert = Alert.objects.create(
        student=student,
        student_class_id=class_id,
        severity=severity,
        trigger_type=Alert.TriggerType.INACTIVITY,
        reason=f"Sinh viên không hoạt động {days_inactive} ngày.",
        evidence={"days_inactive": days_inactive, "last_active": last_event.isoformat()},
        suggested_action="Gửi tin nhắn nhắc nhở và bài tập ngắn.",
        expires_at=_default_expiry(),
    )
    return [alert]


def _check_retry_failures(student, class_id):
    threshold = WARNING_CONFIG["RETRY_FAILURE_THRESHOLD"]

    failed_concepts = (
        TaskAttempt.objects.filter(student=student, is_correct=False)
        .values("task__concept_id", "task__concept__name")
        .annotate(fail_count=Count("id"))
        .filter(fail_count__gte=threshold)
    )

    alerts = []
    for fc in failed_concepts:
        existing = Alert.objects.filter(
            student=student,
            trigger_type=Alert.TriggerType.RETRY_FAILURE,
            concept_id=fc["task__concept_id"],
            status=Alert.AlertStatus.ACTIVE,
        ).exists()
        if existing:
            continue

        alert = Alert.objects.create(
            student=student,
            student_class_id=class_id,
            severity=Alert.Severity.RED,
            trigger_type=Alert.TriggerType.RETRY_FAILURE,
            concept_id=fc["task__concept_id"],
            reason=f"Thất bại {fc['fail_count']} lần ở concept '{fc['task__concept__name']}'.",
            evidence={"concept_id": fc["task__concept_id"], "fail_count": fc["fail_count"]},
            suggested_action="Đặt lịch hỏi nhóm hoặc cung cấp nội dung thay thế.",
            expires_at=_default_expiry(),
        )
        alerts.append(alert)

    return alerts


def _check_milestone_lag(student, class_id):
    pathways = StudentPathway.objects.filter(student=student)
    alerts = []

    for pathway in pathways:
        total = pathway.course.milestones.count()
        if total == 0:
            continue
        completed = len(pathway.milestones_completed or [])
        completion_pct = completed / total

        if completion_pct < 0.3:
            existing = Alert.objects.filter(
                student=student,
                trigger_type=Alert.TriggerType.MILESTONE_LAG,
                status=Alert.AlertStatus.ACTIVE,
            ).exists()
            if existing:
                continue

            alert = Alert.objects.create(
                student=student,
                student_class_id=class_id,
                severity=Alert.Severity.YELLOW,
                trigger_type=Alert.TriggerType.MILESTONE_LAG,
                milestone=pathway.current_milestone,
                reason=f"Tiến độ milestone thấp: {completed}/{total} ({completion_pct:.0%}).",
                evidence={"completed": completed, "total": total},
                suggested_action="Điều chỉnh milestone hoặc tổ chức hỗ trợ nhóm.",
                expires_at=_default_expiry(),
            )
            alerts.append(alert)

    return alerts


def _check_low_mastery(student, class_id):
    min_attempts = WARNING_CONFIG.get("LOW_MASTERY_MIN_ATTEMPTS", 5)
    threshold = WARNING_CONFIG.get("LOW_MASTERY_THRESHOLD", 0.35)

    low_mastery_states = MasteryState.objects.filter(
        student=student,
        p_mastery__lt=threshold,
        attempt_count__gte=min_attempts,
    ).select_related("concept")

    alerts = []
    for state in low_mastery_states:
        existing = Alert.objects.filter(
            student=student,
            trigger_type=Alert.TriggerType.LOW_MASTERY,
            concept_id=state.concept_id,
            status=Alert.AlertStatus.ACTIVE,
        ).exists()
        if existing:
            continue

        alert = Alert.objects.create(
            student=student,
            student_class_id=class_id,
            severity=Alert.Severity.RED,
            trigger_type=Alert.TriggerType.LOW_MASTERY,
            concept_id=state.concept_id,
            reason=(
                f"Mastery khái niệm '{state.concept.name}' chỉ đạt {state.p_mastery:.0%} "
                f"sau {state.attempt_count} lần thử."
            ),
            evidence={
                "concept_id": state.concept_id,
                "p_mastery": round(state.p_mastery, 4),
                "attempt_count": state.attempt_count,
                "correct_count": state.correct_count,
            },
            suggested_action="Cung cấp nội dung bổ trợ hoặc gặp SV trực tiếp.",
            expires_at=_default_expiry(),
        )
        alerts.append(alert)

    return alerts


def get_class_overview(class_id: int) -> dict:
    students = User.objects.filter(
        class_memberships__student_class_id=class_id,
        role=User.Role.STUDENT,
    )
    total = students.count()

    now = timezone.now()
    active_alerts = Alert.objects.filter(
        student_class_id=class_id,
        status=Alert.AlertStatus.ACTIVE,
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    )
    red_students = active_alerts.filter(severity=Alert.Severity.RED).values("student").distinct().count()
    yellow_students = active_alerts.filter(severity=Alert.Severity.YELLOW).values("student").distinct().count()
    on_track = total - red_students - yellow_students

    avg_mastery = MasteryState.objects.filter(
        student__in=students
    ).aggregate(avg=Avg("p_mastery"))["avg"] or 0

    pathways = StudentPathway.objects.filter(student__in=students)
    avg_completion = 0
    if pathways.exists():
        completions = []
        for p in pathways:
            t = p.course.concepts.count()
            completions.append(len(p.concepts_completed or []) / t * 100 if t > 0 else 0)
        avg_completion = sum(completions) / len(completions) if completions else 0

    min_events = WARNING_CONFIG.get("MIN_EVENTS_PER_STUDENT", 5)
    total_events = EventLog.objects.filter(user__in=students).count()
    data_sufficient = total == 0 or (total_events / max(total, 1)) >= min_events

    return {
        "total_students": total,
        "on_track": max(0, on_track),
        "needs_attention": yellow_students,
        "needs_intervention": red_students,
        "active_alerts": active_alerts.count(),
        "avg_mastery": round(avg_mastery, 3),
        "avg_completion_pct": round(avg_completion, 1),
        "data_sufficient": data_sufficient,
    }
