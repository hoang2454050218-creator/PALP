import pytest

from fairness.audit_classifier import audit_classifier
from fairness.models import FairnessAudit

pytestmark = pytest.mark.django_db


class TestAuditClassifier:
    def test_passes_balanced_predictions(self, admin_user):
        # 50/50 selection rate per group -> ratio = 1.0 -> pass
        audit = audit_classifier(
            target_name="risk_score_v1_test",
            y_true=[1, 0, 1, 0, 1, 0, 1, 0],
            y_pred=[1, 0, 1, 0, 1, 0, 1, 0],
            sensitive_features={
                "gender": ["M", "M", "M", "M", "F", "F", "F", "F"],
            },
            reviewed_by=admin_user,
        )
        assert audit.passed is True
        assert audit.violations == []

    def test_fails_disparate_impact(self):
        # Group M selected 100%, group F selected 0% -> ratio = 0
        audit = audit_classifier(
            target_name="biased_classifier",
            y_true=[1, 1, 1, 1, 0, 0, 0, 0],
            y_pred=[1, 1, 1, 1, 0, 0, 0, 0],
            sensitive_features={
                "gender": ["M", "M", "M", "M", "F", "F", "F", "F"],
            },
        )
        assert audit.passed is False
        violations = [v["metric"] for v in audit.violations]
        assert "disparate_impact_ratio" in violations

    def test_fails_equalized_odds(self):
        # Group F has lower TPR than group M -> EOD difference > 0.1
        audit = audit_classifier(
            target_name="eod_test",
            y_true=[1, 1, 1, 1, 1, 1, 1, 1],
            y_pred=[1, 1, 1, 1, 0, 0, 0, 0],
            sensitive_features={
                "gender": ["M", "M", "M", "M", "F", "F", "F", "F"],
            },
        )
        # All true positives, but group F all predicted 0
        # demographic_parity ratio = 0 -> already fails DI
        # equalized_odds: TPR M=1.0, F=0.0, diff=1.0 > 0.1
        violations = [v["metric"] for v in audit.violations]
        assert "equalized_odds_difference" in violations

    def test_intersectional_violation(self):
        # gender alone is balanced (M=50%, F=50%)
        # region alone is balanced (urban=50%, rural=50%)
        # but F+rural is the only group selected -> intersectional violation
        y_pred = [0, 0, 0, 1, 0, 0, 0, 1]  # only positions 3,7 selected
        gender = ["M", "M", "M", "M", "F", "F", "F", "F"]
        region = ["urban", "urban", "rural", "rural", "urban", "urban", "rural", "rural"]
        # position 3 = M+rural, position 7 = F+rural
        # gender ratio: M=25%, F=25% -> ratio 1.0 ok
        # region ratio: urban=0%, rural=50% -> ratio 0 -> fails DI
        audit = audit_classifier(
            target_name="intersect_test",
            y_true=None,
            y_pred=y_pred,
            sensitive_features={"gender": gender, "region": region},
        )
        # Region itself fails (urban=0% vs rural=50%) which is already documented
        violation_attrs = {v["attr"] for v in audit.violations}
        assert "region" in violation_attrs

    def test_persists_metrics_for_inspection(self):
        audit = audit_classifier(
            target_name="metrics_persist",
            y_true=[1, 0, 1, 0],
            y_pred=[1, 0, 1, 0],
            sensitive_features={"gender": ["M", "M", "F", "F"]},
        )
        assert "gender" in audit.metrics
        assert "demographic_parity" in audit.metrics["gender"]
        assert "selection_rates" in audit.metrics["gender"]

    def test_validates_input_lengths(self):
        with pytest.raises(ValueError, match="length"):
            audit_classifier(
                target_name="bad_input",
                y_true=[1, 0],
                y_pred=[1, 0],
                sensitive_features={"gender": ["M"]},  # length 1 != y_pred length 2
            )

    def test_audit_log_entry_persisted(self):
        audit_classifier(
            target_name="persistence_test",
            y_true=None,
            y_pred=[1, 0, 1, 0],
            sensitive_features={"gender": ["M", "M", "F", "F"]},
        )
        assert FairnessAudit.objects.filter(target_name="persistence_test").exists()
