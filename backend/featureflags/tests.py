import pytest

from .models import FeatureFlag
from .services import invalidate_cache, is_enabled

pytestmark = pytest.mark.django_db


class TestIsEnabled:
    def setup_method(self):
        invalidate_cache()

    def test_master_switch_off_returns_false(self, student):
        FeatureFlag.objects.create(name="x.feature", enabled=False, rollout_pct=100)
        invalidate_cache()
        assert is_enabled("x.feature", user=student) is False

    def test_master_switch_on_full_rollout_returns_true(self, student):
        FeatureFlag.objects.create(name="x.feature", enabled=True, rollout_pct=100)
        invalidate_cache()
        assert is_enabled("x.feature", user=student) is True

    def test_zero_rollout_returns_false(self, student):
        FeatureFlag.objects.create(name="x.feature", enabled=True, rollout_pct=0)
        invalidate_cache()
        assert is_enabled("x.feature", user=student) is False

    def test_unknown_flag_returns_false(self, student):
        invalidate_cache()
        assert is_enabled("does.not.exist", user=student) is False

    def test_decision_is_stable_for_same_user(self, student):
        FeatureFlag.objects.create(name="x.feature", enabled=True, rollout_pct=50)
        invalidate_cache()
        first = is_enabled("x.feature", user=student)
        for _ in range(20):
            assert is_enabled("x.feature", user=student) == first

    def test_role_targeting(self, student, lecturer):
        FeatureFlag.objects.create(
            name="x.feature", enabled=True, rollout_pct=100,
            rules_json={"roles": ["lecturer"]},
        )
        invalidate_cache()
        assert is_enabled("x.feature", user=student) is False
        assert is_enabled("x.feature", user=lecturer) is True

    def test_no_user_with_partial_rollout_returns_false(self):
        FeatureFlag.objects.create(name="x.feature", enabled=True, rollout_pct=50)
        invalidate_cache()
        assert is_enabled("x.feature", user=None) is False
