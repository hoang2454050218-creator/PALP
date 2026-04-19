"""Frontier service tests — past-self vs current-self snapshot."""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from adaptive.models import MasteryState
from peer.services.frontier import compute_frontier

pytestmark = pytest.mark.django_db


class TestComputeFrontier:
    def test_returns_zeroes_for_brand_new_student(self, student):
        snap = compute_frontier(student)
        assert snap.current_avg_mastery == 0.0
        assert snap.prior_avg_mastery == 0.0
        assert snap.delta == 0.0
        assert snap.concepts_progressed == []
        assert snap.concepts_regressed == []

    def test_progress_detected_for_recently_updated_state(self, student, concepts):
        c1, c2, _ = concepts
        MasteryState.objects.create(
            student=student, concept=c1, p_mastery=0.7, attempt_count=2,
        )
        MasteryState.objects.create(
            student=student, concept=c2, p_mastery=0.55, attempt_count=4,
        )
        snap = compute_frontier(student)
        assert snap.current_avg_mastery > 0
        assert snap.delta > 0
        assert any(item["concept_id"] == c1.id for item in snap.concepts_progressed)

    def test_old_state_treated_as_stable(self, student, concepts):
        c1 = concepts[0]
        ms = MasteryState.objects.create(
            student=student, concept=c1, p_mastery=0.6, attempt_count=3,
        )
        # Force ``last_updated`` to be older than the lookback window.
        MasteryState.objects.filter(pk=ms.pk).update(
            last_updated=timezone.now() - timedelta(days=120)
        )
        snap = compute_frontier(student)
        # Stable concept => prior == current, no progressed entry.
        assert snap.delta == pytest.approx(0.0)
        assert snap.concepts_progressed == []
        assert snap.concepts_regressed == []

    def test_truncates_to_top_10_progressed(self, student, course, concepts):
        from curriculum.models import Concept

        # Create > 10 concepts so the truncation rule matters.
        many = [
            Concept.objects.create(
                course=course, code=f"X{i}", name=f"Khái niệm {i}", order=10 + i,
            )
            for i in range(12)
        ]
        for idx, c in enumerate(many):
            MasteryState.objects.create(
                student=student, concept=c,
                p_mastery=0.5 + 0.02 * idx, attempt_count=1,
            )
        snap = compute_frontier(student)
        assert len(snap.concepts_progressed) <= 10
