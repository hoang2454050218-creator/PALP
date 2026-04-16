import pytest
from datetime import timedelta

from django.db.models import Avg
from django.utils import timezone

from accounts.models import User
from adaptive.models import MasteryState, TaskAttempt
from analytics.models import KPIDefinition, KPILineageLog
from analytics.services import generate_kpi_snapshot, generate_kpi_snapshot_with_integrity
from events.models import EventLog

pytestmark = [pytest.mark.django_db, pytest.mark.data_qa]


class TestKPIIntegrity:

    def test_snapshot_has_required_keys(self, class_with_members):
        snapshot = generate_kpi_snapshot(class_with_members.id, 1)
        for key in ("week", "cohort_size", "micro_task_completion_rate", "mastery"):
            assert key in snapshot

    def test_cohort_size_matches_members(self, class_with_members):
        snapshot = generate_kpi_snapshot(class_with_members.id, 1)
        assert snapshot["cohort_size"] == 2

    def test_zero_attempts_completion_is_zero(self, class_with_members):
        snapshot = generate_kpi_snapshot(class_with_members.id, 1)
        assert snapshot["micro_task_completion_rate"] == 0


class TestMasteryConsistency:

    def test_average_matches_manual_calculation(
        self, student, student_b, concepts,
    ):
        MasteryState.objects.create(student=student, concept=concepts[0], p_mastery=0.8)
        MasteryState.objects.create(student=student_b, concept=concepts[0], p_mastery=0.4)

        db_avg = MasteryState.objects.aggregate(avg=Avg("p_mastery"))["avg"]
        assert db_avg == pytest.approx(0.6, abs=0.01)


class TestCompletionRate:

    def test_rate_matches_manual(
        self, student, micro_tasks,
    ):
        TaskAttempt.objects.create(
            student=student, task=micro_tasks[0], is_correct=True,
        )
        TaskAttempt.objects.create(
            student=student, task=micro_tasks[0], is_correct=False,
        )
        TaskAttempt.objects.create(
            student=student, task=micro_tasks[1], is_correct=True,
        )

        total = TaskAttempt.objects.count()
        correct = TaskAttempt.objects.filter(is_correct=True).count()
        rate = correct / total * 100
        assert rate == pytest.approx(66.7, abs=0.1)


# ---------------------------------------------------------------------------
# KPI Registry validation
# ---------------------------------------------------------------------------


@pytest.fixture
def _seed_kpi_defs(admin_user):
    now = timezone.now()
    base = {
        "owner": admin_user,
        "baseline_period_start": now - timedelta(days=30),
        "baseline_period_end": now - timedelta(days=16),
        "intervention_period_start": now - timedelta(days=14),
        "intervention_period_end": now + timedelta(days=60),
    }
    KPIDefinition.objects.create(
        code="active_learning_time", name="ALT",
        description="x", unit="minutes", target_value=20,
        target_direction=KPIDefinition.TargetDirection.INCREASE,
        source_events=["session_started", "session_ended"],
        query_function="analytics.services._compute_active_learning_time_with_lineage",
        **base,
    )
    KPIDefinition.objects.create(
        code="micro_task_completion", name="MTC",
        description="x", unit="%", target_value=70,
        target_direction=KPIDefinition.TargetDirection.ABSOLUTE,
        source_events=["micro_task_completed"],
        query_function="analytics.services._compute_completion_rate_with_lineage",
        **base,
    )


class TestKPIRegistryValidation:

    def test_all_kpis_have_owners(self, _seed_kpi_defs):
        for kpi in KPIDefinition.objects.all():
            assert kpi.owner_id is not None

    def test_all_kpis_have_source_events_or_manual(self, _seed_kpi_defs):
        for kpi in KPIDefinition.objects.all():
            has_events = len(kpi.source_events) > 0
            is_manual = kpi.code == "csat_score"
            assert has_events or is_manual, f"{kpi.code} has no source"

    def test_all_kpis_have_query_function(self, _seed_kpi_defs):
        for kpi in KPIDefinition.objects.all():
            assert kpi.query_function, f"{kpi.code} missing query_function"

    def test_baseline_intervention_no_overlap(self, _seed_kpi_defs):
        for kpi in KPIDefinition.objects.all():
            if kpi.baseline_period_end and kpi.intervention_period_start:
                assert kpi.baseline_period_end <= kpi.intervention_period_start

    def test_integrity_snapshot_produces_lineage(
        self, _seed_kpi_defs, student, class_with_members,
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

        generate_kpi_snapshot_with_integrity(class_with_members.id, 1)
        assert KPILineageLog.objects.count() > 0
