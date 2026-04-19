from signals.scoring import (
    compute_focus_minutes,
    compute_frustration_score,
    compute_idle_minutes,
    compute_session_quality,
)


class TestFocusMinutes:
    def test_full_focus_when_no_away(self):
        assert compute_focus_minutes([], total_window_seconds=300) == 5.0

    def test_partial_away(self):
        # 60 seconds away in a 5-minute window -> 4 minutes focused
        assert compute_focus_minutes([60_000], total_window_seconds=300) == 4.0

    def test_clamps_at_zero(self):
        assert compute_focus_minutes([10_000_000], total_window_seconds=300) == 0.0


class TestIdleMinutes:
    def test_sums_durations(self):
        assert compute_idle_minutes([60_000, 30_000]) == 1.5

    def test_empty(self):
        assert compute_idle_minutes([]) == 0.0


class TestFrustrationScore:
    def test_uses_max(self):
        assert compute_frustration_score([0.1, 0.5, 0.9, 0.3]) == 0.9

    def test_clamps_at_one(self):
        assert compute_frustration_score([1.5]) == 1.0

    def test_empty_returns_zero(self):
        assert compute_frustration_score([]) == 0.0


class TestSessionQuality:
    def test_high_quality_focused_no_frustration(self):
        q = compute_session_quality(focus_minutes=4.5, idle_minutes=0.5, frustration_score=0.0, give_up_count=0)
        assert q > 0.85

    def test_drops_with_frustration(self):
        no_frust = compute_session_quality(4.5, 0.5, 0.0, 0)
        high_frust = compute_session_quality(4.5, 0.5, 0.8, 0)
        assert high_frust < no_frust

    def test_drops_with_give_ups(self):
        no_giveup = compute_session_quality(4.5, 0.5, 0.0, 0)
        with_giveup = compute_session_quality(4.5, 0.5, 0.0, 3)
        assert with_giveup < no_giveup

    def test_zero_when_no_activity(self):
        assert compute_session_quality(0.0, 0.0, 0.0, 0) == 0.0
