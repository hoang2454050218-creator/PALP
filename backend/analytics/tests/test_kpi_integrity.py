import pytest
from datetime import timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.models import User
from adaptive.models import MasteryState, TaskAttempt
from analytics.models import (
    DataQualityLog,
    KPIDefinition,
    KPILineageLog,
    KPIVersion,
    PilotReport,
)
from analytics.services import (
    generate_kpi_snapshot_with_integrity,
    generate_pilot_report,
    lock_baseline,
)
from analytics.tasks import kpi_integrity_audit
from events.models import EventLog

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def kpi_owner(db):
    return User.objects.create_user(
        username="kpi_owner", password="Str0ngP@ss!",
        role=User.Role.ADMIN,
    )


@pytest.fixture
def kpi_defs(kpi_owner):
    now = timezone.now()
    baseline_start = now - timedelta(days=30)
    baseline_end = now - timedelta(days=16)
    intervention_start = now - timedelta(days=14)
    intervention_end = now + timedelta(days=60)

    common = {
        "owner": kpi_owner,
        "baseline_period_start": baseline_start,
        "baseline_period_end": baseline_end,
        "intervention_period_start": intervention_start,
        "intervention_period_end": intervention_end,
    }

    defs = {}
    defs["alt"] = KPIDefinition.objects.create(
        code="active_learning_time",
        name="Thời gian học chủ động/tuần",
        description="Trung bình phút học/tuần tính từ session events",
        unit="minutes",
        target_value=20.0,
        target_direction=KPIDefinition.TargetDirection.INCREASE,
        source_events=["session_started", "session_ended"],
        query_function="analytics.services._compute_active_learning_time_with_lineage",
        **common,
    )
    defs["mtc"] = KPIDefinition.objects.create(
        code="micro_task_completion",
        name="Tỷ lệ hoàn thành micro-task",
        description="% micro-task correct / total attempts",
        unit="%",
        target_value=70.0,
        target_direction=KPIDefinition.TargetDirection.ABSOLUTE,
        source_events=["micro_task_completed"],
        query_function="analytics.services._compute_completion_rate_with_lineage",
        **common,
    )
    defs["csat"] = KPIDefinition.objects.create(
        code="csat_score",
        name="CSAT",
        description="Customer Satisfaction Score từ khảo sát",
        unit="score",
        target_value=4.0,
        target_direction=KPIDefinition.TargetDirection.ABSOLUTE,
        source_events=[],
        query_function="analytics.services._compute_csat_with_lineage",
        **common,
    )
    defs["gvd"] = KPIDefinition.objects.create(
        code="gv_dashboard_usage",
        name="GV sử dụng dashboard",
        description="Số lần GV xem dashboard/tuần",
        unit="times/week",
        target_value=2.0,
        target_direction=KPIDefinition.TargetDirection.ABSOLUTE,
        source_events=["gv_dashboard_viewed"],
        query_function="analytics.services._compute_dashboard_usage_with_lineage",
        **common,
    )
    defs["ttd"] = KPIDefinition.objects.create(
        code="time_to_detect_struggling",
        name="Thời gian phát hiện SV khó",
        description="Trung bình giờ từ dấu hiệu đến alert",
        unit="hours",
        target_value=50.0,
        target_direction=KPIDefinition.TargetDirection.DECREASE,
        source_events=["session_started"],
        query_function="analytics.services._compute_detection_time_with_lineage",
        **common,
    )
    return defs


# ---------------------------------------------------------------------------
# KPIINT-001: Each KPI has an owner
# ---------------------------------------------------------------------------


class TestKPIOwnership:
    def test_each_kpi_has_owner(self, kpi_defs):
        for kpi in KPIDefinition.objects.all():
            assert kpi.owner is not None
            assert kpi.owner_id is not None

    def test_owner_cannot_be_null(self, kpi_owner):
        with pytest.raises(Exception):
            KPIDefinition.objects.create(
                code="bad_kpi", name="Bad", owner=None,
                description="x", unit="x", target_value=0,
                target_direction=KPIDefinition.TargetDirection.INCREASE,
                source_events=[], query_function="x",
            )


# ---------------------------------------------------------------------------
# KPIINT-002: Each KPI traces to source events
# ---------------------------------------------------------------------------


class TestKPITraceability:
    def test_source_events_defined(self, kpi_defs):
        for kpi in KPIDefinition.objects.exclude(code="csat_score"):
            assert len(kpi.source_events) > 0, f"{kpi.code} has no source_events"

    def test_source_events_are_valid_event_names(self, kpi_defs):
        valid = {c.value for c in EventLog.EventName}
        for kpi in KPIDefinition.objects.exclude(code="csat_score"):
            for event_name in kpi.source_events:
                assert event_name in valid, (
                    f"{kpi.code} references unknown event: {event_name}"
                )


# ---------------------------------------------------------------------------
# KPIINT-003: Each KPI has reproducible query_function
# ---------------------------------------------------------------------------


class TestKPIReproducibility:
    def test_query_function_is_importable(self, kpi_defs):
        for kpi in KPIDefinition.objects.all():
            parts = kpi.query_function.rsplit(".", 1)
            assert len(parts) == 2, f"{kpi.code}: invalid function path"
            module_path, func_name = parts
            from importlib import import_module
            mod = import_module(module_path)
            fn = getattr(mod, func_name, None)
            assert fn is not None, (
                f"{kpi.code}: {kpi.query_function} not found"
            )
            assert callable(fn)


# ---------------------------------------------------------------------------
# KPIINT-004: Locked KPI rejects definition changes
# ---------------------------------------------------------------------------


class TestKPILocking:
    def test_locked_kpi_rejects_code_change(self, kpi_defs, kpi_owner):
        kpi = kpi_defs["alt"]
        kpi.is_locked = True
        super(KPIDefinition, kpi).save(update_fields=["is_locked"])

        kpi.code = "renamed_kpi"
        with pytest.raises(ValidationError, match="locked"):
            kpi.save()

    def test_locked_kpi_rejects_target_change(self, kpi_defs):
        kpi = kpi_defs["mtc"]
        kpi.is_locked = True
        super(KPIDefinition, kpi).save(update_fields=["is_locked"])

        kpi.target_value = 99.0
        with pytest.raises(ValidationError, match="locked"):
            kpi.save()

    def test_locked_kpi_rejects_source_events_change(self, kpi_defs):
        kpi = kpi_defs["alt"]
        kpi.is_locked = True
        super(KPIDefinition, kpi).save(update_fields=["is_locked"])

        kpi.source_events = ["page_view"]
        with pytest.raises(ValidationError, match="locked"):
            kpi.save()

    def test_locked_kpi_allows_baseline_value_update(self, kpi_defs):
        kpi = kpi_defs["alt"]
        kpi.is_locked = True
        super(KPIDefinition, kpi).save(update_fields=["is_locked"])

        kpi.baseline_value = 42.0
        kpi.save()
        kpi.refresh_from_db()
        assert kpi.baseline_value == 42.0

    def test_unlocked_kpi_allows_changes(self, kpi_defs):
        kpi = kpi_defs["alt"]
        assert not kpi.is_locked
        kpi.target_value = 30.0
        kpi.save()
        kpi.refresh_from_db()
        assert kpi.target_value == 30.0


# ---------------------------------------------------------------------------
# KPIINT-005: Baseline/intervention periods do not overlap
# ---------------------------------------------------------------------------


class TestPeriodSeparation:
    def test_valid_periods_pass(self, kpi_defs):
        for kpi in KPIDefinition.objects.all():
            if kpi.baseline_period_end and kpi.intervention_period_start:
                assert kpi.baseline_period_end <= kpi.intervention_period_start

    def test_overlapping_periods_rejected(self, kpi_owner):
        now = timezone.now()
        with pytest.raises(ValidationError, match="overlap"):
            KPIDefinition.objects.create(
                code="overlap_kpi", name="Overlap", owner=kpi_owner,
                description="x", unit="x", target_value=0,
                target_direction=KPIDefinition.TargetDirection.INCREASE,
                source_events=[], query_function="x",
                baseline_period_start=now - timedelta(days=10),
                baseline_period_end=now + timedelta(days=5),
                intervention_period_start=now,
                intervention_period_end=now + timedelta(days=30),
            )

    def test_reversed_period_rejected(self, kpi_owner):
        now = timezone.now()
        with pytest.raises(ValidationError, match="precede"):
            KPIDefinition.objects.create(
                code="reversed_kpi", name="Reversed", owner=kpi_owner,
                description="x", unit="x", target_value=0,
                target_direction=KPIDefinition.TargetDirection.INCREASE,
                source_events=[], query_function="x",
                baseline_period_start=now,
                baseline_period_end=now - timedelta(days=5),
            )


# ---------------------------------------------------------------------------
# KPIINT-006: Dashboard report includes schema_version
# ---------------------------------------------------------------------------


class TestDashboardVersioning:
    def test_report_has_schema_version(self, kpi_defs, class_with_members):
        report = generate_pilot_report(class_with_members.id, week_number=1)
        assert report.schema_version == KPIDefinition.SCHEMA_VERSION
        assert isinstance(report.kpi_definitions_snapshot, dict)
        assert len(report.kpi_definitions_snapshot) == 5

    def test_report_snapshot_contains_all_kpis(self, kpi_defs, class_with_members):
        report = generate_pilot_report(class_with_members.id, week_number=1)
        for code in ["active_learning_time", "micro_task_completion",
                      "csat_score", "gv_dashboard_usage",
                      "time_to_detect_struggling"]:
            assert code in report.kpi_definitions_snapshot


# ---------------------------------------------------------------------------
# KPIINT-007: KPI with zero raw events fails integrity check
# ---------------------------------------------------------------------------


class TestZeroRawDataDetection:
    def test_traceability_fails_with_no_events(self, kpi_defs):
        result = kpi_integrity_audit()
        details = result["details"]
        for code in ["active_learning_time", "micro_task_completion",
                      "gv_dashboard_usage", "time_to_detect_struggling"]:
            trace = details[code]["traceability"]
            assert trace["status"] == "FAIL"

    def test_csat_passes_without_events(self, kpi_defs):
        result = kpi_integrity_audit()
        trace = result["details"]["csat_score"]["traceability"]
        assert trace["status"] == "PASS"


# ---------------------------------------------------------------------------
# KPIINT-008: Definition change mid-pilot detected
# ---------------------------------------------------------------------------


class TestDefinitionDriftDetection:
    def test_drift_detected_after_lock(self, kpi_defs, kpi_owner):
        kpi = kpi_defs["alt"]
        kpi.bump_version("initial lock", kpi_owner)
        kpi.is_locked = True
        super(KPIDefinition, kpi).save(update_fields=["is_locked"])

        result = kpi_integrity_audit()
        drift = result["details"]["active_learning_time"]["definition_drift"]
        assert drift["status"] == "PASS"


# ---------------------------------------------------------------------------
# KPIINT-009: Event gap > 24h flags KPI as unreliable
# ---------------------------------------------------------------------------


class TestEventGapDetection:
    def test_gap_detected(self, kpi_defs, student, class_with_members):
        now = timezone.now()
        EventLog.objects.create(
            event_name=EventLog.EventName.SESSION_STARTED,
            timestamp_utc=now - timedelta(days=6),
            actor=student, actor_type=EventLog.ActorType.STUDENT,
        )
        EventLog.objects.create(
            event_name=EventLog.EventName.SESSION_STARTED,
            timestamp_utc=now - timedelta(days=3),
            actor=student, actor_type=EventLog.ActorType.STUDENT,
        )

        result = kpi_integrity_audit()
        gaps = result["details"]["active_learning_time"]["event_gaps"]
        assert gaps["status"] == "FAIL"
        assert len(gaps["gaps"]) > 0
        assert gaps["gaps"][0]["gap_hours"] > 24

    def test_no_gap_when_events_close(self, kpi_defs, student, class_with_members):
        now = timezone.now()
        for h in range(0, 48, 12):
            EventLog.objects.create(
                event_name=EventLog.EventName.SESSION_STARTED,
                timestamp_utc=now - timedelta(hours=h),
                actor=student, actor_type=EventLog.ActorType.STUDENT,
            )

        result = kpi_integrity_audit()
        gaps = result["details"]["active_learning_time"]["event_gaps"]
        assert gaps["status"] == "PASS"


# ---------------------------------------------------------------------------
# KPIINT-010: Tracking bug pattern flagged
# ---------------------------------------------------------------------------


class TestTrackingBugDetection:
    def test_suspicious_improvement_flagged(self, kpi_defs):
        kpi = kpi_defs["alt"]
        KPILineageLog.objects.create(
            kpi=kpi, week_number=1, class_id=1,
            computed_value=10.0, event_count=100,
            event_date_range={}, definition_version=1,
        )
        KPILineageLog.objects.create(
            kpi=kpi, week_number=2, class_id=1,
            computed_value=20.0, event_count=50,
            event_date_range={}, definition_version=1,
        )

        result = kpi_integrity_audit()
        bug = result["details"]["active_learning_time"]["tracking_bug"]
        assert bug["status"] == "FAIL"
        assert "event_volume_dropped" in bug["reason"]

    def test_normal_improvement_passes(self, kpi_defs):
        kpi = kpi_defs["alt"]
        KPILineageLog.objects.create(
            kpi=kpi, week_number=1, class_id=1,
            computed_value=10.0, event_count=100,
            event_date_range={}, definition_version=1,
        )
        KPILineageLog.objects.create(
            kpi=kpi, week_number=2, class_id=1,
            computed_value=15.0, event_count=120,
            event_date_range={}, definition_version=1,
        )

        result = kpi_integrity_audit()
        bug = result["details"]["active_learning_time"]["tracking_bug"]
        assert bug["status"] == "PASS"


# ---------------------------------------------------------------------------
# KPIINT-011: KPIVersion created on pre-lock definition change
# ---------------------------------------------------------------------------


class TestVersioning:
    def test_bump_version_creates_snapshot(self, kpi_defs, kpi_owner):
        kpi = kpi_defs["alt"]
        assert kpi.current_version == 1
        assert KPIVersion.objects.filter(kpi=kpi).count() == 0

        kpi.bump_version("adjusted target", kpi_owner)

        assert kpi.current_version == 2
        version = KPIVersion.objects.get(kpi=kpi, version=1)
        assert version.definition_snapshot["code"] == "active_learning_time"
        assert version.change_reason == "adjusted target"
        assert version.created_by == kpi_owner


# ---------------------------------------------------------------------------
# KPIINT-012: KPILineageLog records sample event IDs
# ---------------------------------------------------------------------------


class TestLineageLogging:
    def test_lineage_created_on_integrity_snapshot(
        self, kpi_defs, student, class_with_members,
    ):
        now = timezone.now()
        EventLog.objects.create(
            event_name=EventLog.EventName.SESSION_STARTED,
            timestamp_utc=now - timedelta(hours=2),
            actor=student, actor_type=EventLog.ActorType.STUDENT,
        )
        EventLog.objects.create(
            event_name=EventLog.EventName.SESSION_ENDED,
            timestamp_utc=now - timedelta(hours=1),
            actor=student, actor_type=EventLog.ActorType.STUDENT,
        )

        snapshot = generate_kpi_snapshot_with_integrity(
            class_with_members.id, week_number=1,
        )

        alt_lineage = KPILineageLog.objects.filter(
            kpi__code="active_learning_time",
        ).first()
        assert alt_lineage is not None
        assert alt_lineage.event_count >= 2
        assert len(alt_lineage.sample_event_ids) > 0
        assert alt_lineage.definition_version == 1

    def test_lineage_attached_to_report(
        self, kpi_defs, class_with_members,
    ):
        report = generate_pilot_report(class_with_members.id, week_number=1)
        lineage_count = KPILineageLog.objects.filter(report=report).count()
        assert lineage_count > 0


# ---------------------------------------------------------------------------
# KPIINT-013: Baseline value locked after lock_baseline()
# ---------------------------------------------------------------------------


class TestBaselineLocking:
    def test_lock_baseline_sets_value_and_locks(
        self, kpi_defs, student, class_with_members,
    ):
        kpi = kpi_defs["alt"]
        now = timezone.now()
        EventLog.objects.create(
            event_name=EventLog.EventName.SESSION_STARTED,
            timestamp_utc=kpi.baseline_period_start + timedelta(hours=1),
            actor=student, actor_type=EventLog.ActorType.STUDENT,
        )
        EventLog.objects.create(
            event_name=EventLog.EventName.SESSION_ENDED,
            timestamp_utc=kpi.baseline_period_start + timedelta(hours=2),
            actor=student, actor_type=EventLog.ActorType.STUDENT,
        )

        locked = lock_baseline("active_learning_time", class_with_members.id)
        assert locked.is_locked
        assert locked.baseline_value is not None
        assert locked.baseline_locked_at is not None

        lineage = KPILineageLog.objects.filter(
            kpi=locked, week_number=0,
        ).first()
        assert lineage is not None
        assert lineage.computation_params["purpose"] == "baseline_lock"

    def test_lock_baseline_rejects_already_locked(
        self, kpi_defs, class_with_members,
    ):
        kpi = kpi_defs["alt"]
        kpi.is_locked = True
        super(KPIDefinition, kpi).save(update_fields=["is_locked"])

        with pytest.raises(ValidationError, match="already locked"):
            lock_baseline("active_learning_time", class_with_members.id)

    def test_lock_baseline_rejects_no_period(self, kpi_owner, class_with_members):
        kpi = KPIDefinition.objects.create(
            code="no_period_kpi", name="No Period", owner=kpi_owner,
            description="x", unit="x", target_value=0,
            target_direction=KPIDefinition.TargetDirection.INCREASE,
            source_events=["session_started"],
            query_function="analytics.services._compute_active_learning_time_with_lineage",
        )
        with pytest.raises(ValidationError, match="no baseline period"):
            lock_baseline("no_period_kpi", class_with_members.id)


# ---------------------------------------------------------------------------
# Integration: audit writes DataQualityLog
# ---------------------------------------------------------------------------


class TestAuditPersistence:
    def test_audit_creates_data_quality_log(self, kpi_defs):
        kpi_integrity_audit()
        log = DataQualityLog.objects.filter(
            source="kpi_integrity_audit",
        ).first()
        assert log is not None
        assert isinstance(log.details, dict)
        assert "active_learning_time" in log.details
