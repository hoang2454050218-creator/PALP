"""Reciprocal matcher tests — both directions required, no one-way."""
from __future__ import annotations

import pytest

from adaptive.models import MasteryState
from peer.models import PeerConsent, PeerCohort, ReciprocalPeerMatch
from peer.services.reciprocal_matcher import find_reciprocal_match
from privacy.models import ConsentRecord
from privacy.constants import CONSENT_VERSION

pytestmark = pytest.mark.django_db


def _grant_teaching(*users):
    for u in users:
        ConsentRecord.objects.create(
            user=u, purpose="peer_teaching", granted=True, version=CONSENT_VERSION,
        )
        PeerConsent.objects.update_or_create(
            student=u, defaults={"peer_teaching": True},
        )


def _set_mastery(student, concept, value):
    MasteryState.objects.update_or_create(
        student=student, concept=concept,
        defaults={"p_mastery": value, "attempt_count": 5},
    )


@pytest.fixture
def cohort(class_with_members, student, student_b):
    cohort = PeerCohort.objects.create(
        student_class=class_with_members,
        ability_band_label="band_0",
        members_count=2,
    )
    cohort.members.set([student, student_b])
    return cohort


class TestFindReciprocalMatch:
    def test_returns_none_without_consent(self, student, student_b, concepts, cohort):
        _set_mastery(student, concepts[0], 0.9)
        _set_mastery(student_b, concepts[1], 0.9)
        # Only one side opts in.
        _grant_teaching(student)
        assert find_reciprocal_match(student) is None

    def test_returns_none_when_no_reciprocity_possible(
        self, student, student_b, concepts, cohort,
    ):
        _grant_teaching(student, student_b)
        # Both students share the same strength/weakness — no opportunity
        # for reciprocal teaching.
        _set_mastery(student, concepts[0], 0.9)
        _set_mastery(student_b, concepts[0], 0.85)
        assert find_reciprocal_match(student) is None

    def test_creates_match_when_reciprocal_pair_exists(
        self, student, student_b, concepts, cohort,
    ):
        _grant_teaching(student, student_b)
        c1, c2, _ = concepts
        # A is strong on c1, weak on c2 -- B is the mirror.
        _set_mastery(student, c1, 0.9)
        _set_mastery(student, c2, 0.2)
        _set_mastery(student_b, c1, 0.2)
        _set_mastery(student_b, c2, 0.9)

        match = find_reciprocal_match(student)
        assert match is not None
        assert match.student_a_id == student.id
        assert match.student_b_id == student_b.id
        assert match.concept_a_to_b_id == c1.id
        assert match.concept_b_to_a_id == c2.id
        assert match.compatibility_score > 0

    def test_idempotent_does_not_duplicate_match(
        self, student, student_b, concepts, cohort,
    ):
        _grant_teaching(student, student_b)
        c1, c2, _ = concepts
        _set_mastery(student, c1, 0.9)
        _set_mastery(student, c2, 0.2)
        _set_mastery(student_b, c1, 0.2)
        _set_mastery(student_b, c2, 0.9)

        m1 = find_reciprocal_match(student)
        m2 = find_reciprocal_match(student)
        assert m1.id == m2.id
        assert ReciprocalPeerMatch.objects.filter(
            student_a=student, student_b=student_b,
        ).count() == 1
