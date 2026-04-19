"""Cohort builder tests — k-means + fairness gate."""
from __future__ import annotations

import pytest

from accounts.models import ClassMembership
from adaptive.models import MasteryState
from peer.models import PeerCohort
from peer.services.cohort_builder import build_cohorts

pytestmark = pytest.mark.django_db


def _seed(student, concepts, scores):
    for concept, score in zip(concepts, scores):
        MasteryState.objects.update_or_create(
            student=student, concept=concept,
            defaults={"p_mastery": score, "attempt_count": 5},
        )


class TestBuildCohorts:
    def test_no_eligible_members_returns_empty(self, student_class):
        results = build_cohorts(student_class)
        assert results == []

    def test_creates_single_cohort_for_small_class(
        self, class_with_members, student, student_b, concepts, settings,
    ):
        # COHORT_TARGET_SIZE=25 + only 2 students => one cohort.
        # Lower MIN_SIZE so the small class isn't merged away to nothing.
        settings.PALP_PEER = {
            **settings.PALP_PEER, "COHORT_MIN_SIZE": 1, "COHORT_TARGET_SIZE": 25,
        }
        _seed(student, concepts, [0.4, 0.5, 0.6])
        _seed(student_b, concepts, [0.6, 0.7, 0.8])
        results = build_cohorts(class_with_members)
        assert len(results) == 1
        assert results[0].members == 2

    def test_marks_previous_cohorts_inactive(
        self, class_with_members, student, student_b, concepts, settings,
    ):
        settings.PALP_PEER = {**settings.PALP_PEER, "COHORT_MIN_SIZE": 1}
        _seed(student, concepts, [0.4, 0.5, 0.6])
        _seed(student_b, concepts, [0.6, 0.7, 0.8])

        first = build_cohorts(class_with_members)
        assert first
        old_cohort_id = first[0].cohort_id

        second = build_cohorts(class_with_members)
        assert second

        old = PeerCohort.objects.get(pk=old_cohort_id)
        assert old.is_active is False

    def test_skips_students_without_mastery_data(
        self, class_with_members, student, student_b, concepts, settings,
    ):
        settings.PALP_PEER = {**settings.PALP_PEER, "COHORT_MIN_SIZE": 1}
        # Only ``student`` has data; ``student_b`` is not seeded.
        _seed(student, concepts, [0.5, 0.5, 0.5])

        results = build_cohorts(class_with_members)
        assert len(results) == 1
        assert results[0].members == 1
