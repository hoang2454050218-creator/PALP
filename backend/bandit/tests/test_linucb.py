"""LinUCB engine + DB-aware service tests."""
from __future__ import annotations

import numpy as np
import pytest

from bandit.linucb import LinUCBArmState, select, update
from bandit.models import (
    BanditArm,
    BanditDecision,
    BanditExperiment,
    BanditReward,
    LinUCBArmState as DBLinUCBArmState,
)
from bandit.services import record_reward_linucb, select_arm_linucb


class TestPureEngine:
    def test_select_picks_best_when_only_one_arm(self):
        states = [LinUCBArmState.fresh(arm_id=1, dim=3)]
        choice = select(states=states, context=[1.0, 0.0, 0.0])
        assert choice.arm_id == 1

    def test_update_changes_state(self):
        s = LinUCBArmState.fresh(arm_id=1, dim=3)
        s2 = update(s, context=[1.0, 0.0, 0.0], reward=1.0)
        assert not np.allclose(s.A, s2.A)
        assert not np.allclose(s.b, s2.b)

    def test_after_many_rewards_exploitation_dominates(self):
        good = LinUCBArmState.fresh(arm_id=1, dim=2)
        bad = LinUCBArmState.fresh(arm_id=2, dim=2)
        for _ in range(50):
            good = update(good, context=[1.0, 0.5], reward=1.0)
            bad = update(bad, context=[1.0, 0.5], reward=0.0)
        choice = select(states=[good, bad], context=[1.0, 0.5], alpha=0.1)
        assert choice.arm_id == 1

    def test_dimension_mismatch_raises(self):
        s = LinUCBArmState.fresh(arm_id=1, dim=3)
        try:
            select(states=[s], context=[1.0, 0.0])
        except ValueError:
            pass
        else:
            raise AssertionError("Expected dim mismatch ValueError")


@pytest.mark.django_db
class TestServiceIntegration:
    def _experiment(self):
        exp = BanditExperiment.objects.create(
            key="nudge_dispatch_v2", title="LinUCB nudge",
            status=BanditExperiment.Status.ACTIVE,
        )
        BanditArm.objects.create(experiment=exp, key="arm_a", title="Arm A")
        BanditArm.objects.create(experiment=exp, key="arm_b", title="Arm B")
        return exp

    def test_select_persists_decision_and_state(self, student):
        self._experiment()
        result = select_arm_linucb(
            experiment_key="nudge_dispatch_v2",
            user=student,
            context=[1.0, 0.5, 0.0],
        )
        assert isinstance(result.decision, BanditDecision)
        assert DBLinUCBArmState.objects.filter(arm=result.arm).exists()
        assert result.confidence >= 0.0

    def test_record_reward_updates_db_state(self, student):
        self._experiment()
        result = select_arm_linucb(
            experiment_key="nudge_dispatch_v2",
            user=student,
            context=[1.0, 0.0, 0.0],
        )
        before = DBLinUCBArmState.objects.get(arm=result.arm)
        before_a = list(before.matrix_a)
        record_reward_linucb(
            decision=result.decision,
            context=[1.0, 0.0, 0.0],
            value=1.0,
        )
        after = DBLinUCBArmState.objects.get(arm=result.arm)
        assert after.matrix_a != before_a
        assert BanditReward.objects.filter(decision=result.decision).exists()

    def test_dimension_persistence(self, student):
        self._experiment()
        select_arm_linucb(
            experiment_key="nudge_dispatch_v2",
            user=student,
            context=[1.0, 0.5, 0.0],
        )
        try:
            select_arm_linucb(
                experiment_key="nudge_dispatch_v2",
                user=student,
                context=[1.0, 0.5],
            )
        except ValueError as exc:
            assert "dim" in str(exc).lower()
        else:
            raise AssertionError("Expected dimension mismatch")
