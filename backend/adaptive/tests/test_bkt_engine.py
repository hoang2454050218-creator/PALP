import pytest
from django.conf import settings

from adaptive.engine import update_mastery, decide_pathway_action, get_mastery_state
from adaptive.models import MasteryState, ContentIntervention
from curriculum.models import SupplementaryContent

pytestmark = pytest.mark.django_db

THRESHOLDS = settings.PALP_ADAPTIVE_THRESHOLDS
BKT_DEFAULTS = settings.PALP_BKT_DEFAULTS


class TestInitialMasteryState:
    def test_initial_p_mastery_equals_p_l0(self, student, concepts):
        state = get_mastery_state(student.id, concepts[0].id)
        assert state.p_mastery == pytest.approx(BKT_DEFAULTS["P_L0"])


class TestUpdateMastery:
    def test_correct_answer_increases_mastery(self, student, concepts):
        initial = get_mastery_state(student.id, concepts[0].id)
        p_before = initial.p_mastery
        updated = update_mastery(student.id, concepts[0].id, is_correct=True)
        assert updated.p_mastery > p_before

    def test_wrong_answer_from_high_mastery_decreases(self, student, concepts):
        state = get_mastery_state(student.id, concepts[0].id)
        state.p_mastery = 0.90
        state.save()
        updated = update_mastery(student.id, concepts[0].id, is_correct=False)
        assert updated.p_mastery < 0.90

    def test_mastery_bounded_below(self, student, concepts):
        state = get_mastery_state(student.id, concepts[0].id)
        state.p_mastery = 0.02
        state.save()
        updated = update_mastery(student.id, concepts[0].id, is_correct=False)
        assert updated.p_mastery >= 0.01

    def test_mastery_bounded_above(self, student, concepts):
        state = get_mastery_state(student.id, concepts[0].id)
        state.p_mastery = 0.98
        state.save()
        updated = update_mastery(student.id, concepts[0].id, is_correct=True)
        assert updated.p_mastery <= 0.99

    def test_consecutive_correct_pushes_mastery_above_half(self, student, concepts):
        concept_id = concepts[0].id
        for _ in range(10):
            state = update_mastery(student.id, concept_id, is_correct=True)
        assert state.p_mastery > 0.5

    def test_consecutive_wrong_pushes_mastery_down(self, student, concepts):
        concept_id = concepts[0].id
        state = get_mastery_state(student.id, concept_id)
        state.p_mastery = 0.7
        state.save()
        for _ in range(5):
            state = update_mastery(student.id, concept_id, is_correct=False)
        assert state.p_mastery < 0.7


class TestDecidePathwayAction:
    def test_low_mastery_returns_supplement(self, student, concepts):
        state = get_mastery_state(student.id, concepts[0].id)
        state.p_mastery = THRESHOLDS["MASTERY_LOW"] - 0.1
        state.save()
        result = decide_pathway_action(student.id, concepts[0].id)
        assert result["action"] == "supplement"
        assert result["difficulty_adjustment"] == -1

    def test_high_mastery_with_enough_attempts_returns_advance(self, student, concepts):
        state = get_mastery_state(student.id, concepts[0].id)
        state.p_mastery = THRESHOLDS["MASTERY_HIGH"] + 0.05
        state.attempt_count = THRESHOLDS["MIN_ATTEMPTS_FOR_ADVANCE"] + 1
        state.save()
        result = decide_pathway_action(student.id, concepts[0].id)
        assert result["action"] == "advance"
        assert result["difficulty_adjustment"] == 1

    def test_medium_mastery_returns_continue(self, student, concepts):
        mid = (THRESHOLDS["MASTERY_LOW"] + THRESHOLDS["MASTERY_HIGH"]) / 2
        state = get_mastery_state(student.id, concepts[0].id)
        state.p_mastery = mid
        state.save()
        result = decide_pathway_action(student.id, concepts[0].id)
        assert result["action"] == "continue"
        assert result["difficulty_adjustment"] == 0

    def test_supplementary_content_returned_when_low_mastery(self, student, concepts):
        SupplementaryContent.objects.create(
            concept=concepts[0],
            title="Extra material",
            content_type=SupplementaryContent.ContentType.TEXT,
            body="Review content",
            difficulty_target=1,
            order=1,
        )
        state = get_mastery_state(student.id, concepts[0].id)
        state.p_mastery = THRESHOLDS["MASTERY_LOW"] - 0.1
        state.save()
        result = decide_pathway_action(student.id, concepts[0].id)
        assert result["action"] == "supplement"
        assert result["supplementary_content"] is not None
        assert result["supplementary_content"]["title"] == "Extra material"


class TestContentInterventionLogging:
    def test_supplement_action_logs_intervention(self, student, concepts):
        state = get_mastery_state(student.id, concepts[0].id)
        state.p_mastery = THRESHOLDS["MASTERY_LOW"] - 0.1
        state.save()
        decide_pathway_action(student.id, concepts[0].id)
        assert ContentIntervention.objects.filter(
            student=student,
            concept=concepts[0],
            intervention_type=ContentIntervention.InterventionType.SUPPLEMENTARY,
        ).exists()

    def test_advance_action_logs_intervention(self, student, concepts):
        state = get_mastery_state(student.id, concepts[0].id)
        state.p_mastery = THRESHOLDS["MASTERY_HIGH"] + 0.05
        state.attempt_count = THRESHOLDS["MIN_ATTEMPTS_FOR_ADVANCE"] + 1
        state.save()
        decide_pathway_action(student.id, concepts[0].id)
        assert ContentIntervention.objects.filter(
            student=student,
            concept=concepts[0],
            intervention_type=ContentIntervention.InterventionType.DIFFICULTY_UP,
        ).exists()
