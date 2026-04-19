import pytest

from fairness.metrics import (
    calibration_per_group,
    concentration_ratio,
    demographic_parity,
    equalized_odds,
    false_positive_rates,
    selection_rates,
    true_positive_rates,
)


class TestSelectionRates:
    def test_balanced_groups(self):
        rates = selection_rates([1, 0, 1, 0], ["a", "a", "b", "b"])
        assert rates == {"a": 0.5, "b": 0.5}

    def test_one_group_only(self):
        rates = selection_rates([1, 1, 0], ["a", "a", "a"])
        assert rates == {"a": pytest.approx(2 / 3)}


class TestDemographicParity:
    def test_perfectly_fair(self):
        result = demographic_parity([1, 0, 1, 0], ["a", "a", "b", "b"])
        assert result["difference"] == 0.0
        assert result["ratio"] == 1.0

    def test_unfair_4_5_rule(self):
        # group a: 100% selected, group b: 50% selected
        result = demographic_parity([1, 1, 1, 0], ["a", "a", "b", "b"])
        assert result["ratio"] == pytest.approx(0.5)
        assert result["difference"] == pytest.approx(0.5)

    def test_single_group_returns_safe_default(self):
        result = demographic_parity([1, 0, 1], ["a", "a", "a"])
        assert result["note"] == "single_group"
        assert result["ratio"] == 1.0


class TestTPR:
    def test_basic(self):
        # group a: y_true=[1,0,1,1], y_pred=[1,0,1,0] -> TPR = 2/3
        # group b: y_true=[1,0],     y_pred=[0,1]    -> TPR = 0
        tpr = true_positive_rates(
            [1, 0, 1, 1, 1, 0],
            [1, 0, 1, 0, 0, 1],
            ["a", "a", "a", "a", "b", "b"],
        )
        assert tpr["a"] == pytest.approx(2 / 3)
        assert tpr["b"] == 0.0


class TestFPR:
    def test_basic(self):
        # group a: y_true=[0,0,1], y_pred=[1,0,1] -> FPR = 1/2
        fpr = false_positive_rates([0, 0, 1], [1, 0, 1], ["a", "a", "a"])
        assert fpr["a"] == pytest.approx(0.5)


class TestEqualizedOdds:
    def test_perfect_equality(self):
        result = equalized_odds(
            [1, 0, 1, 0],
            [1, 0, 1, 0],
            ["a", "a", "b", "b"],
        )
        assert result["difference"] == 0.0

    def test_tpr_disparity_picked_up(self):
        # group a perfect, group b miscalls all positives
        result = equalized_odds(
            [1, 1, 1, 1],
            [1, 1, 0, 0],
            ["a", "a", "b", "b"],
        )
        assert result["tpr_difference"] == pytest.approx(1.0)


class TestCalibration:
    def test_well_calibrated(self):
        result = calibration_per_group(
            [1, 0, 1, 0],
            [0.9, 0.1, 0.9, 0.1],
            ["a", "a", "b", "b"],
        )
        # Both groups identical scores -> identical Brier
        assert result["max_minus_min"] == pytest.approx(0.0, abs=1e-9)


class TestConcentrationRatio:
    def test_balanced(self):
        members = [{"g": "M"}, {"g": "F"}]
        pop = [{"g": "M"}, {"g": "F"}, {"g": "M"}, {"g": "F"}]
        result = concentration_ratio(members, pop, lambda m: m["g"])
        assert result["cluster"] == {"M": 0.5, "F": 0.5}
        assert result["concentration"]["M"] == pytest.approx(1.0)

    def test_concentrated(self):
        members = [{"g": "F"}] * 9 + [{"g": "M"}]
        pop = [{"g": "M"}] * 50 + [{"g": "F"}] * 50
        result = concentration_ratio(members, pop, lambda m: m["g"])
        assert result["cluster"]["F"] == pytest.approx(0.9)
        assert result["concentration"]["F"] == pytest.approx(1.8)
