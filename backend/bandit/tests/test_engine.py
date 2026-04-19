"""Bandit engine tests — pure functions, no DB."""
from __future__ import annotations

import numpy as np
import pytest

from bandit.engine import (
    ArmPosteriorState,
    thompson_select,
    update_posterior,
)


class TestThompsonSelect:
    def test_picks_dominating_arm_eventually(self):
        """The arm with much higher alpha/beta should win MOST of the time."""
        rng = np.random.default_rng(42)
        posteriors = [
            ArmPosteriorState(arm_id=1, alpha=20, beta=5),    # high reward
            ArmPosteriorState(arm_id=2, alpha=2, beta=20),    # low reward
        ]
        wins = {1: 0, 2: 0}
        for _ in range(200):
            choice = thompson_select(posteriors=posteriors, rng=rng)
            wins[choice.arm_id] += 1
        # Should pick the high-reward arm > 80% of the time.
        assert wins[1] > 160

    def test_uniform_prior_is_balanced(self):
        rng = np.random.default_rng(7)
        posteriors = [
            ArmPosteriorState(arm_id=1, alpha=1, beta=1),
            ArmPosteriorState(arm_id=2, alpha=1, beta=1),
        ]
        wins = {1: 0, 2: 0}
        for _ in range(500):
            choice = thompson_select(posteriors=posteriors, rng=rng)
            wins[choice.arm_id] += 1
        # Should be roughly 50/50.
        assert 200 <= wins[1] <= 300

    def test_empty_posteriors_raises(self):
        rng = np.random.default_rng()
        with pytest.raises(ValueError):
            thompson_select(posteriors=[], rng=rng)

    def test_returns_samples_dict_for_all_arms(self):
        rng = np.random.default_rng(1)
        posteriors = [
            ArmPosteriorState(arm_id=1, alpha=2, beta=5),
            ArmPosteriorState(arm_id=2, alpha=5, beta=2),
            ArmPosteriorState(arm_id=3, alpha=3, beta=3),
        ]
        choice = thompson_select(posteriors=posteriors, rng=rng)
        assert set(choice.samples) == {1, 2, 3}


class TestUpdatePosterior:
    def test_full_reward_increments_alpha_only(self):
        new_alpha, new_beta = update_posterior(alpha=1, beta=1, reward=1.0)
        assert new_alpha == pytest.approx(2.0)
        assert new_beta == pytest.approx(1.0)

    def test_zero_reward_increments_beta_only(self):
        new_alpha, new_beta = update_posterior(alpha=1, beta=1, reward=0.0)
        assert new_alpha == pytest.approx(1.0)
        assert new_beta == pytest.approx(2.0)

    def test_partial_reward_splits(self):
        new_alpha, new_beta = update_posterior(alpha=1, beta=1, reward=0.3)
        assert new_alpha == pytest.approx(1.3)
        assert new_beta == pytest.approx(1.7)

    def test_clamps_out_of_range_reward(self):
        new_alpha, new_beta = update_posterior(alpha=1, beta=1, reward=2.5)
        assert new_alpha == pytest.approx(2.0)  # clamped to 1.0
        new_alpha, new_beta = update_posterior(alpha=1, beta=1, reward=-0.5)
        assert new_beta == pytest.approx(2.0)  # clamped to 0.0
