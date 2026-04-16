"""
Backfill legacy EventLog records to populate new schema fields.

Usage:
    python manage.py backfill_events [--batch-size 500] [--dry-run]
"""
from django.core.management.base import BaseCommand
from django.db.models import F
from events.models import EventLog


class Command(BaseCommand):
    help = "Backfill actor_type and event_version for pre-upgrade EventLog rows"

    def add_arguments(self, parser):
        parser.add_argument("--batch-size", type=int, default=500)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]

        self.stdout.write("Backfilling event_version for legacy events...")
        legacy_qs = EventLog.objects.filter(event_version="")
        count = legacy_qs.count()
        self.stdout.write(f"  Found {count} events with empty event_version")
        if not dry_run and count > 0:
            updated = legacy_qs.update(event_version="0.9")
            self.stdout.write(self.style.SUCCESS(f"  Updated {updated} records"))

        self.stdout.write("Backfilling actor_type from user role...")
        for role_val, actor_type in [
            ("student", EventLog.ActorType.STUDENT),
            ("lecturer", EventLog.ActorType.LECTURER),
            ("admin", EventLog.ActorType.ADMIN),
        ]:
            qs = EventLog.objects.filter(
                actor_type="",
                actor__role=role_val,
            )
            count = qs.count()
            self.stdout.write(f"  {role_val}: {count} events to update")
            if not dry_run and count > 0:
                total = 0
                while True:
                    ids = list(qs.values_list("id", flat=True)[:batch_size])
                    if not ids:
                        break
                    updated = EventLog.objects.filter(id__in=ids).update(actor_type=actor_type)
                    total += updated
                self.stdout.write(self.style.SUCCESS(f"  Updated {total} records"))

        orphan = EventLog.objects.filter(actor_type="", actor__isnull=True).count()
        if orphan > 0:
            self.stdout.write(f"Setting {orphan} actor-less events to 'system'...")
            if not dry_run:
                EventLog.objects.filter(
                    actor_type="", actor__isnull=True
                ).update(actor_type=EventLog.ActorType.SYSTEM)

        self.stdout.write(self.style.SUCCESS("Backfill complete."))
