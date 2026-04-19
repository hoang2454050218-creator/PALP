"""Celery tasks for the Peer Engine.

Three scheduled jobs:

* ``peer.weekly_recompute_cohorts`` — Sunday 03:00 ICT.
* ``peer.daily_detect_herds`` — every day 04:00 ICT.
* ``peer.prompt_optin_after_4w`` — Monday 09:00 ICT.

All three are idempotent — re-running them produces the same artefact
set (subject to data changes) and never duplicates rows.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("palp.peer.tasks")


@shared_task(name="peer.weekly_recompute_cohorts")
def weekly_recompute_cohorts() -> dict:
    """Re-cluster every active class into same-ability cohorts."""
    from accounts.models import StudentClass
    from peer.services.cohort_builder import build_cohorts

    summary = {"classes": 0, "cohorts": 0, "audit_failures": 0}
    for student_class in StudentClass.objects.all():
        results = build_cohorts(student_class)
        summary["classes"] += 1
        summary["cohorts"] += len(results)
        summary["audit_failures"] += sum(
            0 if r.fairness_passed else 1 for r in results
        )
    logger.info("weekly_recompute_cohorts done: %s", summary)
    return summary


@shared_task(name="peer.daily_detect_herds")
def daily_detect_herds() -> dict:
    """Detect new herd clusters across every active class."""
    from accounts.models import StudentClass
    from peer.services.cluster_detector import detect_herd_clusters

    summary = {"classes": 0, "clusters": 0, "flagged": 0}
    for student_class in StudentClass.objects.all():
        results = detect_herd_clusters(student_class)
        summary["classes"] += 1
        summary["clusters"] += len(results)
        summary["flagged"] += sum(1 for r in results if r.flagged_for_review)
    logger.info("daily_detect_herds done: %s", summary)
    return summary


@shared_task(name="peer.prompt_optin_after_4w")
def prompt_optin_after_4w() -> dict:
    """Surface the 4-week opt-in prompt for students who have not seen it."""
    from accounts.models import User
    from peer.models import PeerConsent

    cutoff = timezone.now() - timedelta(days=28)
    candidates = User.objects.filter(
        date_joined__lte=cutoff,
        role="student",
    )

    surfaced = 0
    for student in candidates:
        consent, _ = PeerConsent.objects.get_or_create(student=student)
        if consent.prompt_shown_at:
            continue
        if consent.peer_comparison or consent.peer_teaching:
            consent.prompt_shown_at = timezone.now()
            consent.save(update_fields=["prompt_shown_at"])
            continue
        consent.prompt_shown_at = timezone.now()
        consent.save(update_fields=["prompt_shown_at"])
        surfaced += 1

    logger.info("prompt_optin_after_4w surfaced=%s", surfaced)
    return {"surfaced": surfaced}
