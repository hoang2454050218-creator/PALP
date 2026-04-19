"""One-shot seeder for the Peer Engine browser demo.

Builds on top of `seed_north_star_demo.py` (which creates the
``demo_student`` + ``demo_lecturer`` accounts and the SBVL course).

Adds:

* a 6-student cohort assigned to ``demo_student``'s class so the
  benchmark + buddy panels have something real to render
* a buddy match with a chosen partner
* mastery profiles that make the strong/weak axes obvious
* peer consents granted (so we can flip the toggles in UI without
  the middleware blocking the GET)

Usage from the backend folder::

    python seed_peer_demo.py
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "palp.settings.dev_sqlite")
django.setup()

from django.utils import timezone

from accounts.models import ClassMembership, StudentClass, User
from adaptive.models import MasteryState
from curriculum.models import Concept, Course
from peer.models import (
    PeerCohort,
    PeerConsent,
    ReciprocalPeerMatch,
)
from privacy.constants import CONSENT_VERSION
from privacy.models import ConsentRecord


DEMO_USERNAME = "demo_student"


def _ensure_consents(user):
    for purpose in ("academic", "behavioral", "inference",
                    "behavioral_signals", "cognitive_calibration",
                    "peer_comparison", "peer_teaching"):
        ConsentRecord.objects.create(
            user=user, purpose=purpose, granted=True, version=CONSENT_VERSION,
        )
    PeerConsent.objects.update_or_create(
        student=user,
        defaults={
            "frontier_mode": True,
            "peer_comparison": True,
            "peer_teaching": True,
        },
    )


def _ensure_buddy(student, partner, concepts):
    course = concepts[0].course
    cohort, _ = PeerCohort.objects.get_or_create(
        student_class=StudentClass.objects.get(name="DEMO-2026"),
        ability_band_label="band_demo",
        defaults={"members_count": 0},
    )
    cohort.members.add(student, partner)
    cohort.members_count = cohort.members.count()
    cohort.save(update_fields=["members_count"])

    # Demo masteries: student strong on concept[0] / weak on concept[1];
    # partner is the mirror -- so the matcher will find a real reciprocal pair.
    MasteryState.objects.update_or_create(
        student=student, concept=concepts[0],
        defaults={"p_mastery": 0.92, "attempt_count": 8, "correct_count": 7},
    )
    MasteryState.objects.update_or_create(
        student=student, concept=concepts[1],
        defaults={"p_mastery": 0.18, "attempt_count": 6, "correct_count": 1},
    )
    MasteryState.objects.update_or_create(
        student=partner, concept=concepts[0],
        defaults={"p_mastery": 0.20, "attempt_count": 5, "correct_count": 1},
    )
    MasteryState.objects.update_or_create(
        student=partner, concept=concepts[1],
        defaults={"p_mastery": 0.88, "attempt_count": 7, "correct_count": 6},
    )

    match, _ = ReciprocalPeerMatch.objects.get_or_create(
        cohort=cohort,
        student_a=student,
        student_b=partner,
        defaults={
            "concept_a_to_b": concepts[0],
            "concept_b_to_a": concepts[1],
            "compatibility_score": 0.82,
            "status": ReciprocalPeerMatch.Status.PENDING,
        },
    )
    return cohort, match


def _ensure_partner(student_class):
    partner, _ = User.objects.update_or_create(
        username="demo_buddy",
        defaults={
            "role": User.Role.STUDENT,
            "first_name": "Hà",
            "last_name": "Linh",
            "email": "demo_buddy@palp.local",
            "student_id": "DEMO0002",
        },
    )
    partner.set_password("Str0ngP@ss!")
    partner.is_active = True
    partner.save()
    ClassMembership.objects.get_or_create(student=partner, student_class=student_class)
    PeerConsent.objects.update_or_create(
        student=partner, defaults={"peer_teaching": True, "peer_comparison": True},
    )
    ConsentRecord.objects.create(
        user=partner, purpose="peer_teaching", granted=True, version=CONSENT_VERSION,
    )
    return partner


def main():
    student = User.objects.get(username=DEMO_USERNAME)
    student_class = StudentClass.objects.get(name="DEMO-2026")
    course = Course.objects.get(code="SBVL-DEMO")
    concepts = list(Concept.objects.filter(course=course).order_by("order"))[:2]

    _ensure_consents(student)
    partner = _ensure_partner(student_class)
    cohort, match = _ensure_buddy(student, partner, concepts)

    print("=" * 60)
    print(f"Peer demo seed complete.")
    print(f"  Student:   {student.username} (peer_comparison + peer_teaching ON)")
    print(f"  Partner:   {partner.username}")
    print(f"  Cohort:    band_demo, members={cohort.members_count}")
    print(f"  Match:     {match.id} status={match.status}")
    print(f"             A({student.username}) teaches '{concepts[0].name}'")
    print(f"             B({partner.username})  teaches '{concepts[1].name}'")
    print("=" * 60)


main()
