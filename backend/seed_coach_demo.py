"""One-shot seeder for the Coach browser demo.

Builds on top of seed_north_star_demo.py + seed_peer_demo.py.
Adds the consent records needed so demo_student can chat without
hitting the v1.3 consent re-prompt.
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "palp.settings.dev_sqlite")
django.setup()

from accounts.models import User
from coach.models import CoachConsent
from privacy.constants import CONSENT_PURPOSES, CONSENT_VERSION
from privacy.models import ConsentRecord

DEMO_USERNAME = "demo_student"

student = User.objects.get(username=DEMO_USERNAME)

# Grant the new v1.3 consents AND any prior purposes that may be missing.
for purpose in CONSENT_PURPOSES.keys():
    ConsentRecord.objects.create(
        user=student, purpose=purpose, granted=True, version=CONSENT_VERSION,
    )

CoachConsent.objects.update_or_create(
    student=student,
    defaults={
        "ai_coach_local": True,
        "ai_coach_cloud": False,
        "share_emergency_contact": False,
    },
)

print("=" * 60)
print(f"Coach demo seed complete for {student.username}")
print(f"  All v{CONSENT_VERSION} consents granted")
print("=" * 60)
