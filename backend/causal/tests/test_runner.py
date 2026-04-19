import numpy as np
import pytest

from causal.models import CausalEvaluation, CausalExperiment
from causal.runner import (
    PreRegistrationError,
    evaluate,
    lock,
    register,
)
from experiments.models import Experiment, ExperimentVariant

pytestmark = pytest.mark.django_db


@pytest.fixture
def base_experiment(db):
    e = Experiment.objects.create(
        name="bandit-vs-rule",
        hypothesis="Contextual bandit beats rule-based dispatcher.",
        primary_metric="engagement_24h",
        status=Experiment.Status.DRAFT,
    )
    ExperimentVariant.objects.create(experiment=e, name="control", weight=50)
    ExperimentVariant.objects.create(experiment=e, name="treatment", weight=50)
    return e


@pytest.fixture
def causal_draft(base_experiment, admin_user):
    return register(
        experiment=base_experiment,
        pre_registration="H1: bandit > rule. Outcome: engagement_24h. Estimator: doubly_robust + CUPED.",
        primary_outcome_metric="engagement_24h",
        outcome_kind=CausalExperiment.OutcomeKind.CONTINUOUS,
        cuped_covariate="engagement_pre",
        expected_effect_size=0.3,
        target_sample_per_arm=400,
        irb_reference="IRB-2026-001",
    )


class TestRegister:
    def test_creates_in_draft_state(self, causal_draft):
        assert not causal_draft.is_locked
        assert causal_draft.locked_at is None

    def test_idempotent_in_draft(self, base_experiment, causal_draft):
        # Re-registering while in draft should update fields, not duplicate
        again = register(
            experiment=base_experiment,
            pre_registration="updated text",
            primary_outcome_metric="engagement_24h",
            cuped_covariate="engagement_pre",
            expected_effect_size=0.3,
            target_sample_per_arm=400,
        )
        assert again.pk == causal_draft.pk
        again.refresh_from_db()
        assert again.pre_registration == "updated text"

    def test_rejects_re_register_when_locked(self, base_experiment, causal_draft, admin_user):
        lock(causal_draft, by=admin_user)
        with pytest.raises(PreRegistrationError, match="locked"):
            register(
                experiment=base_experiment,
                pre_registration="new",
                primary_outcome_metric="engagement_24h",
            )


class TestLock:
    def test_locks_draft(self, causal_draft, admin_user):
        lock(causal_draft, by=admin_user)
        causal_draft.refresh_from_db()
        assert causal_draft.is_locked
        assert causal_draft.locked_by == admin_user

    def test_requires_pre_registration_text(self, causal_draft):
        causal_draft.pre_registration = "   "
        causal_draft.save()
        with pytest.raises(PreRegistrationError, match="empty"):
            lock(causal_draft)

    def test_requires_power_analysis(self, base_experiment):
        ce = register(
            experiment=base_experiment,
            pre_registration="H1: x",
            primary_outcome_metric="m",
            # missing effect size + target N
        )
        with pytest.raises(PreRegistrationError, match="Power analysis"):
            lock(ce)


class TestEvaluate:
    def test_refuses_evaluate_before_lock(self, causal_draft):
        with pytest.raises(PreRegistrationError, match="locked"):
            evaluate(
                causal_draft,
                y=[1.0] * 10,
                treatment=[0, 1] * 5,
                estimator=CausalEvaluation.Estimator.NAIVE,
            )

    def test_naive_evaluation_persists(self, causal_draft, admin_user):
        lock(causal_draft, by=admin_user)
        rng = np.random.default_rng(42)
        y = np.concatenate([rng.normal(0, 1, 200), rng.normal(0.5, 1, 200)])
        treatment = np.array([0] * 200 + [1] * 200)
        ev = evaluate(
            causal_draft,
            y=y,
            treatment=treatment,
            estimator=CausalEvaluation.Estimator.NAIVE,
        )
        assert ev.estimator == CausalEvaluation.Estimator.NAIVE
        assert ev.ate is not None
        assert ev.n_treatment == 200
        assert ev.n_control == 200

    def test_cuped_evaluation_with_covariate(self, causal_draft, admin_user):
        lock(causal_draft, by=admin_user)
        rng = np.random.default_rng(42)
        x = rng.normal(0, 1, 400)
        treatment = np.array([0] * 200 + [1] * 200)
        y = x * 0.8 + treatment * 0.3 + rng.normal(0, 0.5, 400)
        ev = evaluate(
            causal_draft,
            y=y,
            treatment=treatment,
            estimator=CausalEvaluation.Estimator.CUPED_NAIVE,
            pre_covariate=x,
        )
        assert abs(ev.ate - 0.3) < 0.1
        assert "variance_reduction" in ev.estimate_json

    def test_dr_requires_all_three_inputs(self, causal_draft, admin_user):
        lock(causal_draft, by=admin_user)
        with pytest.raises(ValueError, match="propensity"):
            evaluate(
                causal_draft,
                y=[1.0] * 10,
                treatment=[0, 1] * 5,
                estimator=CausalEvaluation.Estimator.DOUBLY_ROBUST,
            )

    def test_links_fairness_audit_id(self, causal_draft, admin_user):
        lock(causal_draft, by=admin_user)
        ev = evaluate(
            causal_draft,
            y=[1.0] * 100,
            treatment=[0, 1] * 50,
            estimator=CausalEvaluation.Estimator.NAIVE,
            fairness_audit_id=42,
        )
        assert ev.fairness_audit_id == 42


class TestAmendment:
    def test_amend_after_lock(self, causal_draft, admin_user):
        lock(causal_draft, by=admin_user)
        causal_draft.amend(
            reason="IRB requested wording change",
            diff={"pre_registration": "added clarification on IRB"},
            by=admin_user,
        )
        causal_draft.refresh_from_db()
        assert len(causal_draft.amendments_log) == 1
        assert causal_draft.amendments_log[0]["reason"] == "IRB requested wording change"

    def test_amend_before_lock_rejected(self, causal_draft, admin_user):
        with pytest.raises(ValueError, match="after lock"):
            causal_draft.amend(reason="x", diff={}, by=admin_user)
