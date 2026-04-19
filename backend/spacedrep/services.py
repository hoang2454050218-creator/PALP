"""Spaced repetition service layer."""
from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from spacedrep.engine import (
    FSRSState,
    get_target_retention,
    get_weights,
    initial_state,
    update,
)
from spacedrep.models import ReviewItem, ReviewLog


@transaction.atomic
def ensure_item(*, student, concept) -> ReviewItem:
    """Create the FSRS card for a (student, concept) if missing."""
    item, _ = ReviewItem.objects.get_or_create(
        student=student, concept=concept,
    )
    return item


@transaction.atomic
def review(
    *,
    item: ReviewItem,
    rating: int,
    response_time_seconds: float | None = None,
) -> ReviewLog:
    """Apply one review and persist the new memory state + log row."""
    rating = max(1, min(4, int(rating)))
    weights = get_weights()
    target_retention = get_target_retention()
    now = timezone.now()

    pre_state = FSRSState(stability=float(item.stability), difficulty=float(item.difficulty))

    if item.last_review_at is None:
        new_state = initial_state(rating, weights=weights)
        from spacedrep.engine import next_interval_days

        interval = next_interval_days(new_state.stability, target_retention)
        retrievability = 1.0
    else:
        elapsed = max(0.0, (now - item.last_review_at).total_seconds() / 86400.0)
        result = update(
            state=pre_state,
            rating=rating,
            elapsed_days=elapsed,
            weights=weights,
            target_retention=target_retention,
        )
        new_state = FSRSState(stability=result.stability, difficulty=result.difficulty)
        interval = result.interval_days
        retrievability = result.retrievability_at_review

    log = ReviewLog.objects.create(
        item=item,
        rating=rating,
        response_time_seconds=response_time_seconds,
        pre_stability=pre_state.stability,
        pre_difficulty=pre_state.difficulty,
        post_stability=new_state.stability,
        post_difficulty=new_state.difficulty,
        interval_days=round(interval, 4),
        retrievability_at_review=round(retrievability, 4),
    )

    item.stability = new_state.stability
    item.difficulty = new_state.difficulty
    item.last_review_at = now
    item.due_at = now + timedelta(days=interval)
    item.review_count += 1
    if rating == 1:
        item.lapse_count += 1
        item.state = ReviewItem.State.RELEARNING
    elif item.state == ReviewItem.State.NEW:
        item.state = ReviewItem.State.LEARNING
    elif item.state == ReviewItem.State.LEARNING and item.review_count >= 2:
        item.state = ReviewItem.State.REVIEW
    item.save()

    return log


def due_items(*, student, limit: int = 20):
    """Return items the student should review now or soon."""
    now = timezone.now()
    return list(
        ReviewItem.objects
        .filter(student=student)
        .exclude(state=ReviewItem.State.SUSPENDED)
        .filter(due_at__lte=now + timedelta(hours=12))
        .select_related("concept")
        .order_by("due_at")[:limit]
    )


def upcoming_items(*, student, limit: int = 20):
    """Return items not yet due — sorted by next due date."""
    return list(
        ReviewItem.objects
        .filter(student=student)
        .exclude(state=ReviewItem.State.SUSPENDED)
        .filter(due_at__isnull=False)
        .select_related("concept")
        .order_by("due_at")[:limit]
    )
