import pytest

from adaptive.engine_v2 import (
    AttemptContext,
    autotune_concept,
    effective_correct,
    update_mastery_v2,
)
from adaptive.models import MasteryState, TaskAttempt

pytestmark = pytest.mark.django_db


class TestEffectiveCorrect:
    def test_incorrect_yields_zero(self):
        assert effective_correct(AttemptContext(is_correct=False)) == 0.0

    def test_correct_no_modifiers_yields_one(self):
        assert effective_correct(AttemptContext(is_correct=True)) == 1.0

    def test_each_hint_subtracts_25_pct(self):
        ctx = AttemptContext(is_correct=True, hints_used=1)
        assert effective_correct(ctx) == pytest.approx(0.75, abs=1e-9)
        ctx = AttemptContext(is_correct=True, hints_used=2)
        assert effective_correct(ctx) == pytest.approx(0.5625, abs=1e-9)

    def test_time_penalty_only_above_threshold(self):
        # Within 2x expected -> no penalty
        ctx = AttemptContext(is_correct=True, response_time_ms=4000, expected_response_time_ms=2000)
        assert effective_correct(ctx) == 1.0

    def test_time_penalty_at_3x_expected(self):
        ctx = AttemptContext(is_correct=True, response_time_ms=6000, expected_response_time_ms=2000)
        # ratio 3.0 -> midway through decay band -> 1 - 0.5*(1-0.4) = 0.7
        assert effective_correct(ctx) == pytest.approx(0.7, abs=1e-6)

    def test_time_penalty_clamped_at_floor(self):
        ctx = AttemptContext(is_correct=True, response_time_ms=20000, expected_response_time_ms=2000)
        assert effective_correct(ctx) == pytest.approx(0.4, abs=1e-6)

    def test_combined_penalties_multiply(self):
        ctx = AttemptContext(is_correct=True, hints_used=1, response_time_ms=8000, expected_response_time_ms=2000)
        # ratio 4 -> floor 0.4; hint -> *0.75 -> 0.3
        assert effective_correct(ctx) == pytest.approx(0.3, abs=1e-6)


class TestUpdateMasteryV2:
    def test_correct_attempt_raises_p_mastery_v2(self, student, concepts):
        concept = concepts[0]
        # seed v1 state
        MasteryState.objects.create(
            student=student, concept=concept,
            p_mastery=0.3, p_guess=0.25, p_slip=0.10, p_transit=0.09,
        )
        update_mastery_v2(student.id, concept.id, AttemptContext(is_correct=True))
        state = MasteryState.objects.get(student=student, concept=concept)
        assert state.p_mastery_v2 is not None
        assert state.p_mastery_v2 > 0.3
        # v1 should still be the seeded value
        assert state.p_mastery == 0.3

    def test_v2_with_hints_grows_less_than_clean_correct(self, student, concepts):
        concept = concepts[0]
        MasteryState.objects.create(
            student=student, concept=concept,
            p_mastery=0.3, p_guess=0.25, p_slip=0.10, p_transit=0.09,
        )
        update_mastery_v2(student.id, concept.id, AttemptContext(is_correct=True, hints_used=2))
        state_with_hints = MasteryState.objects.get(student=student, concept=concept)

        # Reset and try clean correct
        MasteryState.objects.filter(student=student, concept=concept).update(p_mastery_v2=None)
        update_mastery_v2(student.id, concept.id, AttemptContext(is_correct=True))
        state_clean = MasteryState.objects.get(student=student, concept=concept)

        assert state_clean.p_mastery_v2 > state_with_hints.p_mastery_v2

    def test_consecutive_correct_grows_monotonically(self, student, concepts):
        concept = concepts[0]
        MasteryState.objects.create(
            student=student, concept=concept,
            p_mastery=0.3, p_guess=0.25, p_slip=0.10, p_transit=0.09,
        )
        prev = 0.3
        # 4 iterations is enough to see growth without hitting the 0.99 clamp.
        for _ in range(4):
            update_mastery_v2(student.id, concept.id, AttemptContext(is_correct=True))
            state = MasteryState.objects.get(student=student, concept=concept)
            assert state.p_mastery_v2 >= prev
            prev = state.p_mastery_v2
        assert prev > 0.95  # converged toward upper bound

    def test_clamped_in_open_unit_interval(self, student, concepts):
        concept = concepts[0]
        MasteryState.objects.create(
            student=student, concept=concept,
            p_mastery=0.99, p_guess=0.25, p_slip=0.10, p_transit=0.09,
        )
        for _ in range(20):
            update_mastery_v2(student.id, concept.id, AttemptContext(is_correct=True))
        state = MasteryState.objects.get(student=student, concept=concept)
        assert 0.01 <= state.p_mastery_v2 <= 0.99


class TestAutotuneConcept:
    def test_returns_priors_when_no_attempts(self, concepts):
        result = autotune_concept(concepts[0].id, [])
        assert result["p_guess"] == pytest.approx(0.25, abs=1e-3)
        assert result["p_slip"] == pytest.approx(0.10, abs=1e-3)

    def test_low_mastery_correct_pushes_p_guess_up(self, student, concepts, micro_tasks):
        concept = concepts[0]
        # Seed a low mastery row
        MasteryState.objects.create(
            student=student, concept=concept,
            p_mastery=0.2, p_guess=0.25, p_slip=0.10, p_transit=0.09,
        )
        # 30 correct attempts despite low mastery -> "guess" pattern
        for _ in range(30):
            TaskAttempt.objects.create(
                student=student, task=micro_tasks[0],
                score=1.0, max_score=1.0, is_correct=True,
            )
        attempts = TaskAttempt.objects.filter(task=micro_tasks[0])
        result = autotune_concept(concept.id, attempts)
        assert result["p_guess"] > 0.25  # nudged up

    def test_high_mastery_wrong_pushes_p_slip_up(self, student, concepts, micro_tasks):
        concept = concepts[0]
        MasteryState.objects.create(
            student=student, concept=concept,
            p_mastery=0.9, p_guess=0.25, p_slip=0.10, p_transit=0.09,
        )
        for _ in range(30):
            TaskAttempt.objects.create(
                student=student, task=micro_tasks[0],
                score=0.0, max_score=1.0, is_correct=False,
            )
        attempts = TaskAttempt.objects.filter(task=micro_tasks[0])
        result = autotune_concept(concept.id, attempts)
        assert result["p_slip"] > 0.10  # nudged up

    def test_invariant_guess_plus_slip_lt_one(self, student, concepts, micro_tasks):
        # Construct attempts that would push both extreme; result must still respect
        # guess + slip < 1 (BKT mathematical invariant).
        concept = concepts[0]
        MasteryState.objects.create(
            student=student, concept=concept,
            p_mastery=0.2, p_guess=0.25, p_slip=0.10, p_transit=0.09,
        )
        for _ in range(50):
            TaskAttempt.objects.create(
                student=student, task=micro_tasks[0],
                score=1.0, max_score=1.0, is_correct=True,
            )
        attempts = TaskAttempt.objects.filter(task=micro_tasks[0])
        result = autotune_concept(concept.id, attempts)
        assert result["p_guess"] + result["p_slip"] < 1.0
