import pytest

from causal.power import (
    sample_size_per_arm_binary,
    sample_size_per_arm_continuous,
)


class TestContinuousPower:
    def test_smaller_effect_needs_more_samples(self):
        n_small = sample_size_per_arm_continuous(0.2)
        n_large = sample_size_per_arm_continuous(0.8)
        assert n_small > n_large

    def test_higher_power_needs_more_samples(self):
        n_80 = sample_size_per_arm_continuous(0.5, power=0.80)
        n_95 = sample_size_per_arm_continuous(0.5, power=0.95)
        assert n_95 > n_80

    def test_known_value_cohen_d_0_5_power_0_8(self):
        # Standard textbook value: cohen's d = 0.5 (medium), power 0.8, alpha 0.05 two-sided
        # ≈ 64 per arm.
        n = sample_size_per_arm_continuous(0.5)
        assert 60 <= n <= 70

    def test_zero_effect_raises(self):
        with pytest.raises(ValueError, match="effect_size"):
            sample_size_per_arm_continuous(0.0)


class TestBinaryPower:
    def test_larger_diff_needs_fewer_samples(self):
        n_small = sample_size_per_arm_binary(0.5, 0.55)
        n_large = sample_size_per_arm_binary(0.5, 0.7)
        assert n_small > n_large

    def test_zero_difference_raises(self):
        with pytest.raises(ValueError, match="differ"):
            sample_size_per_arm_binary(0.5, 0.5)

    def test_invalid_proportion_raises(self):
        with pytest.raises(ValueError, match="\\[0, 1\\]"):
            sample_size_per_arm_binary(1.5, 0.5)
