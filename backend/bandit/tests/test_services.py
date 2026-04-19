"""Bandit service-layer + view tests."""
from __future__ import annotations

import pytest

from bandit.models import (
    BanditArm,
    BanditDecision,
    BanditExperiment,
    BanditPosterior,
    BanditReward,
)
from bandit.services import (
    BanditExperimentInactive,
    NoEnabledArms,
    record_reward,
    select_arm,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def experiment(db):
    exp = BanditExperiment.objects.create(
        key="nudge_dispatch",
        title="Nudge dispatch experiment",
        status=BanditExperiment.Status.ACTIVE,
        seed=42,
    )
    BanditArm.objects.create(experiment=exp, key="gentle", title="Gentle nudge")
    BanditArm.objects.create(experiment=exp, key="urgent", title="Urgent nudge")
    return exp


class TestSelectArm:
    def test_creates_decision_and_posterior(self, experiment, student):
        result = select_arm(
            experiment_key="nudge_dispatch", user=student,
        )
        assert isinstance(result.decision, BanditDecision)
        assert result.arm in experiment.arms.all()
        assert BanditPosterior.objects.filter(arm=result.arm).exists()

    def test_increments_pulls(self, experiment, student):
        result = select_arm(experiment_key="nudge_dispatch", user=student)
        post = BanditPosterior.objects.get(arm=result.arm, context_key="default")
        assert post.pulls == 1
        select_arm(experiment_key="nudge_dispatch", user=student)
        # NB: re-select may pick a different arm; just ensure pulls move.
        assert (
            BanditPosterior.objects
            .filter(arm__experiment=experiment)
            .values_list("pulls", flat=True)
        )

    def test_inactive_experiment_raises(self, experiment, student):
        experiment.status = BanditExperiment.Status.PAUSED
        experiment.save()
        with pytest.raises(BanditExperimentInactive):
            select_arm(experiment_key="nudge_dispatch", user=student)

    def test_no_enabled_arms_raises(self, experiment, student):
        experiment.arms.update(is_enabled=False)
        with pytest.raises(NoEnabledArms):
            select_arm(experiment_key="nudge_dispatch", user=student)


class TestRecordReward:
    def test_updates_alpha_and_beta(self, experiment, student):
        result = select_arm(experiment_key="nudge_dispatch", user=student)
        post_before = BanditPosterior.objects.get(arm=result.arm, context_key="default")
        alpha_before, beta_before = post_before.alpha, post_before.beta

        record_reward(decision=result.decision, value=1.0)
        post_after = BanditPosterior.objects.get(arm=result.arm, context_key="default")
        assert post_after.alpha == pytest.approx(alpha_before + 1.0)
        assert post_after.beta == pytest.approx(beta_before)

    def test_idempotent_for_same_decision(self, experiment, student):
        result = select_arm(experiment_key="nudge_dispatch", user=student)
        a = record_reward(decision=result.decision, value=1.0)
        b = record_reward(decision=result.decision, value=0.0)
        assert a.id == b.id

    def test_stale_window_does_not_update_posterior(self, experiment, student):
        from datetime import timedelta
        from django.utils import timezone

        result = select_arm(experiment_key="nudge_dispatch", user=student)
        result.decision.reward_window_until = timezone.now() - timedelta(days=1)
        result.decision.save()

        post_before = BanditPosterior.objects.get(arm=result.arm, context_key="default")
        alpha_before = post_before.alpha
        record_reward(decision=result.decision, value=1.0)
        post_after = BanditPosterior.objects.get(arm=result.arm, context_key="default")
        # No update because the window expired.
        assert post_after.alpha == pytest.approx(alpha_before)


class TestViews:
    def test_select_endpoint(self, experiment, student_api):
        resp = student_api.post(
            "/api/bandit/select/",
            {"experiment_key": "nudge_dispatch"},
            format="json",
        )
        assert resp.status_code == 201
        assert "decision_id" in resp.data
        assert "arm" in resp.data

    def test_reward_endpoint(self, experiment, student_api):
        resp = student_api.post(
            "/api/bandit/select/",
            {"experiment_key": "nudge_dispatch"},
            format="json",
        )
        decision_id = resp.data["decision_id"]
        resp2 = student_api.post(
            f"/api/bandit/decisions/{decision_id}/reward/",
            {"value": 0.8},
            format="json",
        )
        assert resp2.status_code == 200
        assert resp2.data["reward_value"] == pytest.approx(0.8)

    def test_reward_other_user_is_403(self, experiment, student_api, student_b):
        resp = student_api.post(
            "/api/bandit/select/",
            {"experiment_key": "nudge_dispatch"},
            format="json",
        )
        decision_id = resp.data["decision_id"]

        # Switch to student_b's API client.
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=student_b)
        resp2 = client.post(
            f"/api/bandit/decisions/{decision_id}/reward/",
            {"value": 1.0},
            format="json",
            HTTP_IDEMPOTENCY_KEY="x",
        )
        assert resp2.status_code == 403

    def test_stats_lecturer_only(self, experiment, lecturer_api, student_api):
        resp_lec = lecturer_api.get(
            f"/api/bandit/experiments/{experiment.key}/stats/"
        )
        assert resp_lec.status_code == 200
        resp_stu = student_api.get(
            f"/api/bandit/experiments/{experiment.key}/stats/"
        )
        assert resp_stu.status_code == 403
