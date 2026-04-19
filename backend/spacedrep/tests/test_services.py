"""FSRS service + view tests."""
from __future__ import annotations

import pytest

from spacedrep.models import ReviewItem, ReviewLog
from spacedrep.services import (
    due_items,
    ensure_item,
    review,
    upcoming_items,
)


pytestmark = pytest.mark.django_db


class TestEnsureItem:
    def test_creates_then_returns_existing(self, student, concepts):
        a = ensure_item(student=student, concept=concepts[0])
        b = ensure_item(student=student, concept=concepts[0])
        assert a.id == b.id


class TestReview:
    def test_first_review_initialises_state(self, student, concepts):
        item = ensure_item(student=student, concept=concepts[0])
        log = review(item=item, rating=3)
        item.refresh_from_db()
        assert item.last_review_at is not None
        assert item.due_at is not None
        assert log.interval_days > 0
        assert item.review_count == 1

    def test_again_increments_lapse(self, student, concepts):
        item = ensure_item(student=student, concept=concepts[0])
        review(item=item, rating=3)
        review(item=item, rating=1)
        item.refresh_from_db()
        assert item.lapse_count == 1
        assert item.state == ReviewItem.State.RELEARNING

    def test_review_count_progresses_state(self, student, concepts):
        item = ensure_item(student=student, concept=concepts[0])
        review(item=item, rating=3)
        review(item=item, rating=3)
        review(item=item, rating=3)
        item.refresh_from_db()
        assert item.state == ReviewItem.State.REVIEW

    def test_log_records_pre_and_post(self, student, concepts):
        item = ensure_item(student=student, concept=concepts[0])
        log = review(item=item, rating=3)
        assert log.pre_stability >= 0
        assert log.post_stability >= log.pre_stability  # GOOD shouldn't reduce stability


class TestQueries:
    def test_due_items_includes_just_reviewed(self, student, concepts):
        item = ensure_item(student=student, concept=concepts[0])
        # Force due_at into the past so the query catches it.
        from django.utils import timezone

        item.due_at = timezone.now() - timezone.timedelta(hours=1)
        item.save()
        items = due_items(student=student)
        assert any(i.id == item.id for i in items)

    def test_upcoming_items_orders_by_due(self, student, concepts):
        a = ensure_item(student=student, concept=concepts[0])
        b = ensure_item(student=student, concept=concepts[1])
        from django.utils import timezone

        a.due_at = timezone.now() + timezone.timedelta(days=10)
        a.save()
        b.due_at = timezone.now() + timezone.timedelta(days=2)
        b.save()
        items = upcoming_items(student=student)
        assert items[0].id == b.id


class TestViews:
    def test_review_endpoint_validates_rating(self, student_api, concepts):
        resp = student_api.post(
            "/api/spacedrep/review/",
            {"concept_id": concepts[0].id, "rating": 9},
            format="json",
        )
        assert resp.status_code == 400

    def test_review_endpoint_persists(self, student_api, concepts):
        resp = student_api.post(
            "/api/spacedrep/review/",
            {"concept_id": concepts[0].id, "rating": 3},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["item"]["concept_id"] == concepts[0].id
        assert resp.data["log"]["interval_days"] > 0

    def test_due_endpoint(self, student_api, student, concepts):
        item = ensure_item(student=student, concept=concepts[0])
        from django.utils import timezone

        item.due_at = timezone.now() - timezone.timedelta(hours=1)
        item.save()
        resp = student_api.get("/api/spacedrep/due/")
        assert resp.status_code == 200
        assert any(i["concept_id"] == concepts[0].id for i in resp.data["items"])
