"""FSRS-4.5 engine unit tests — pure functions."""
from __future__ import annotations

import pytest

from spacedrep.engine import (
    FSRSState,
    initial_state,
    next_interval_days,
    retrievability_after,
    update,
)


class TestInitialState:
    def test_again_gives_smallest_stability(self):
        again = initial_state(rating=1)
        easy = initial_state(rating=4)
        assert again.stability < easy.stability

    def test_difficulty_within_bounds(self):
        for r in (1, 2, 3, 4):
            s = initial_state(rating=r)
            assert 1.0 <= s.difficulty <= 10.0


class TestRetrievability:
    def test_full_at_t_zero(self):
        assert retrievability_after(stability=10, elapsed_days=0) == pytest.approx(1.0)

    def test_decays_with_time(self):
        a = retrievability_after(stability=10, elapsed_days=1)
        b = retrievability_after(stability=10, elapsed_days=10)
        assert a > b

    def test_stable_item_decays_slower(self):
        weak = retrievability_after(stability=2, elapsed_days=10)
        strong = retrievability_after(stability=20, elapsed_days=10)
        assert strong > weak


class TestUpdate:
    def test_again_reduces_stability(self):
        s = FSRSState(stability=20.0, difficulty=5.0)
        result = update(state=s, rating=1, elapsed_days=15)
        assert result.stability < s.stability

    def test_easy_increases_stability(self):
        s = FSRSState(stability=10.0, difficulty=5.0)
        result = update(state=s, rating=4, elapsed_days=10)
        assert result.stability > s.stability

    def test_interval_grows_with_easy_streak(self):
        s = FSRSState(stability=5.0, difficulty=5.0)
        result_good = update(state=s, rating=3, elapsed_days=4)
        result_easy = update(state=s, rating=4, elapsed_days=4)
        assert result_easy.interval_days > result_good.interval_days

    def test_difficulty_clamped(self):
        s = FSRSState(stability=10.0, difficulty=10.0)
        # Repeated AGAIN should not push difficulty above 10.
        out = update(state=s, rating=1, elapsed_days=5)
        assert 1.0 <= out.difficulty <= 10.0


class TestNextInterval:
    def test_higher_stability_means_longer_interval(self):
        a = next_interval_days(stability=2)
        b = next_interval_days(stability=20)
        assert b > a

    def test_higher_retention_means_shorter_interval(self):
        a = next_interval_days(stability=10, retention=0.7)
        b = next_interval_days(stability=10, retention=0.95)
        assert a > b
