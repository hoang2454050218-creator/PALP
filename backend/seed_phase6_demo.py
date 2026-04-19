"""One-shot seeder for Phase 6 (XAI + FSRS + DP + Copilot) browser demo."""
import os
from datetime import date, timedelta

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "palp.settings.dev_sqlite")
django.setup()

from django.utils import timezone

from accounts.models import User
from curriculum.models import Concept, Course
from privacy.constants import CONSENT_PURPOSES, CONSENT_VERSION
from privacy.models import ConsentRecord
from privacy_dp.models import EpsilonBudget
from spacedrep.services import ensure_item, review


DEMO_USERNAME = "demo_student"


def main() -> None:
    student = User.objects.get(username=DEMO_USERNAME)

    # Re-grant ALL purposes at the bumped v1.5 version so the demo
    # student doesn't trip the consent re-prompt.
    for purpose in CONSENT_PURPOSES.keys():
        ConsentRecord.objects.create(
            user=student, purpose=purpose, granted=True, version=CONSENT_VERSION,
        )

    # Seed FSRS items for first 3 concepts of the demo course.
    course = Course.objects.get(code="SBVL-DEMO")
    concepts = list(Concept.objects.filter(course=course).order_by("order"))[:3]

    fsrs_seeded = 0
    for concept in concepts:
        item = ensure_item(student=student, concept=concept)
        review(item=item, rating=3)  # GOOD
        # Push due_at into the past so the panel shows them as due.
        item.due_at = timezone.now() - timedelta(hours=2)
        item.save(update_fields=["due_at"])
        fsrs_seeded += 1

    # Seed a DP epsilon budget for admin dashboard.
    today = date.today()
    EpsilonBudget.objects.update_or_create(
        scope="global:weekly",
        period_start=today - timedelta(days=today.weekday()),
        defaults={
            "period_end": today - timedelta(days=today.weekday()) + timedelta(days=7),
            "epsilon_total": 1.0,
            "description": "Default global weekly DP budget",
        },
    )

    print("=" * 60)
    print(f"Phase 6 demo seed complete for {student.username}")
    print(f"  FSRS items seeded: {fsrs_seeded}")
    print(f"  DP epsilon budget: global:weekly = 1.0")
    print("=" * 60)


main()
