"""Benchmark service tests — anonymous percentile band only."""
from __future__ import annotations

import pytest

from adaptive.models import MasteryState
from peer.models import PeerCohort
from peer.services.benchmark import compute_benchmark

pytestmark = pytest.mark.django_db


def _seed_mastery(student, concepts, value):
    for c in concepts:
        MasteryState.objects.update_or_create(
            student=student, concept=c, defaults={"p_mastery": value},
        )


class TestComputeBenchmark:
    def test_returns_unavailable_when_no_cohort(self, student):
        result = compute_benchmark(student)
        assert result.available is False
        assert result.reason == "cohort_not_assigned"

    def test_returns_unavailable_when_cohort_too_small(
        self, class_with_members, student, student_b, concepts
    ):
        _seed_mastery(student, concepts, 0.5)
        _seed_mastery(student_b, concepts, 0.7)
        cohort = PeerCohort.objects.create(
            student_class=class_with_members,
            ability_band_label="band_0",
            members_count=2,
        )
        cohort.members.set([student, student_b])
        result = compute_benchmark(student)
        assert result.available is False
        assert result.reason == "cohort_too_small"

    def test_returns_band_for_top_quartile(
        self, class_with_members, bulk_students, student, concepts, settings,
    ):
        # Force the small-cohort gate to allow this size for the test.
        settings.PALP_PEER = {**settings.PALP_PEER, "COHORT_MIN_SIZE": 3}

        _seed_mastery(student, concepts, 0.95)
        for s in bulk_students:
            _seed_mastery(s, concepts, 0.4)

        cohort = PeerCohort.objects.create(
            student_class=class_with_members,
            ability_band_label="band_0",
            members_count=1 + len(bulk_students),
        )
        cohort.members.set([student] + bulk_students)

        result = compute_benchmark(student)
        assert result.available is True
        assert result.band == "top_25_pct"
        assert "tiến nhanh nhất" in result.safe_copy

    def test_building_phase_copy_for_bottom_quartile(
        self, class_with_members, bulk_students, student, concepts, settings,
    ):
        settings.PALP_PEER = {**settings.PALP_PEER, "COHORT_MIN_SIZE": 3}

        _seed_mastery(student, concepts, 0.05)
        for s in bulk_students:
            _seed_mastery(s, concepts, 0.7)

        cohort = PeerCohort.objects.create(
            student_class=class_with_members,
            ability_band_label="band_0",
            members_count=1 + len(bulk_students),
        )
        cohort.members.set([student] + bulk_students)

        result = compute_benchmark(student)
        assert result.available is True
        assert result.band == "building_phase"
        # Anti-tự-ti rule — copy must NOT mention rank or "below".
        assert "dưới" not in result.safe_copy
        assert "xây nền tảng" in result.safe_copy
