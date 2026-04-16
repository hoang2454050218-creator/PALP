import pytest
from django.core.cache import cache

from adaptive.engine import get_mastery_state, update_mastery
from adaptive.models import MasteryState

pytestmark = [pytest.mark.django_db, pytest.mark.recovery]


class TestMasteryWithoutCache:

    def test_get_mastery_works_after_cache_clear(self, student, concepts):
        state = get_mastery_state(student.id, concepts[0].id)
        cache.clear()
        state_again = get_mastery_state(student.id, concepts[0].id)
        assert state_again.pk == state.pk
        assert state_again.p_mastery == state.p_mastery

    def test_update_mastery_works_after_cache_clear(self, student, concepts):
        get_mastery_state(student.id, concepts[0].id)
        cache.clear()
        updated = update_mastery(student.id, concepts[0].id, is_correct=True)
        assert updated.attempt_count == 1


class TestCacheConsistency:

    def test_update_refreshes_cache(self, student, concepts):
        state = get_mastery_state(student.id, concepts[0].id)
        p_before = state.p_mastery
        update_mastery(student.id, concepts[0].id, is_correct=True)
        cached = get_mastery_state(student.id, concepts[0].id)
        assert cached.p_mastery > p_before

    def test_repeated_updates_keep_cache_in_sync(self, student, concepts):
        for correct in [True, False, True, True]:
            update_mastery(student.id, concepts[0].id, is_correct=correct)
        cached = get_mastery_state(student.id, concepts[0].id)
        db_state = MasteryState.objects.get(student=student, concept=concepts[0])
        assert cached.p_mastery == pytest.approx(db_state.p_mastery)
        assert cached.attempt_count == db_state.attempt_count
