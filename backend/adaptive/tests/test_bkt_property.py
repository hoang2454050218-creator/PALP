import pytest
from hypothesis import given, settings as hyp_settings, strategies as st

from adaptive.engine import update_mastery, get_mastery_state

pytestmark = pytest.mark.django_db


def _apply_sequence(student_id, concept_id, answers):
    for is_correct in answers:
        state = update_mastery(student_id, concept_id, is_correct=is_correct)
    return state


class TestMasteryBounds:
    @given(answers=st.lists(st.booleans(), min_size=1, max_size=30))
    @hyp_settings(max_examples=50, deadline=None)
    def test_mastery_stays_in_bounds(self, answers, student, concepts):
        state = _apply_sequence(student.id, concepts[0].id, answers)
        assert 0.01 <= state.p_mastery <= 0.99

        state.p_mastery = 0.3
        state.attempt_count = 0
        state.correct_count = 0
        state.save()


class TestMasteryDirection:
    def test_correct_answer_never_decreases_mastery(self, student, concepts):
        concept_id = concepts[0].id
        for _ in range(20):
            before = get_mastery_state(student.id, concept_id).p_mastery
            after = update_mastery(student.id, concept_id, is_correct=True).p_mastery
            assert after >= before

    def test_wrong_answer_from_high_mastery_decreases(self, student, concepts):
        concept_id = concepts[0].id
        state = get_mastery_state(student.id, concept_id)
        state.p_mastery = 0.85
        state.save()
        before = state.p_mastery
        after = update_mastery(student.id, concept_id, is_correct=False).p_mastery
        assert after < before


class TestMasteryConvergence:
    def test_many_correct_exceeds_threshold(self, student, concepts):
        concept_id = concepts[0].id
        for _ in range(30):
            state = update_mastery(student.id, concept_id, is_correct=True)
        assert state.p_mastery > 0.85
