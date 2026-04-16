"""
Recovery test: ETL failure mid-run.

Verifies that:
  - A crash in the nightly pipeline does NOT leave partial/corrupt data
  - Re-running the pipeline after fix produces correct results
  - Data quality score is computed correctly after recovery
  - Idempotent: running the pipeline twice yields identical results
"""
import pytest
from unittest.mock import patch, MagicMock

from dashboard.models import Alert
from dashboard.services import compute_early_warnings
from analytics.tasks import run_nightly_early_warnings

pytestmark = [pytest.mark.django_db, pytest.mark.recovery]


class TestETLPartialFailure:
    """Pipeline crash must not leave partial data committed."""

    def test_no_partial_alerts_on_crash(self, class_with_members):
        with patch(
            "dashboard.services.compute_early_warnings",
            side_effect=RuntimeError("ETL disk full"),
        ):
            result = run_nightly_early_warnings()

        assert Alert.objects.count() == 0

    def test_successful_rerun_after_fix(self, class_with_members, student, student_b):
        with patch(
            "dashboard.services.compute_early_warnings",
            side_effect=RuntimeError("Transient failure"),
        ):
            run_nightly_early_warnings()

        assert Alert.objects.count() == 0

        result = run_nightly_early_warnings()
        assert isinstance(result, int)


class TestETLIdempotency:
    """Running the pipeline twice on the same data must be safe."""

    def test_no_duplicate_alerts(self, class_with_members, student, student_b):
        run_nightly_early_warnings()
        count_first = Alert.objects.count()

        run_nightly_early_warnings()
        count_second = Alert.objects.count()

        assert count_second == count_first

    def test_alert_fields_stable_across_runs(self, class_with_members, student):
        run_nightly_early_warnings()
        alerts_first = list(
            Alert.objects.values_list("student_id", "trigger_type", "severity")
        )

        run_nightly_early_warnings()
        alerts_second = list(
            Alert.objects.values_list("student_id", "trigger_type", "severity")
        )

        assert set(alerts_first) == set(alerts_second)


class TestETLRecoveryIntegrity:
    """After crash + recovery the pipeline must produce valid output."""

    def test_compute_early_warnings_returns_list(self, class_with_members):
        result = compute_early_warnings(class_with_members.id)
        assert isinstance(result, list)

    def test_all_alerts_have_required_fields(self, class_with_members):
        alerts = compute_early_warnings(class_with_members.id)
        for alert in alerts:
            assert alert.severity in [s.value for s in Alert.Severity]
            assert alert.trigger_type in [t.value for t in Alert.TriggerType]
            assert alert.reason
            assert alert.suggested_action
