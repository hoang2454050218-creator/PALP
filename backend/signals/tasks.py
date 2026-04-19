"""
Celery tasks for behavioural signal rollup + retention enforcement.
"""
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from accounts.models import User

from .services import rollup_day


@shared_task(name="signals.rollup_signals_daily")
def rollup_signals_daily(target_date_iso: str | None = None) -> dict:
    """Compute BehaviorScore per active student for ``target_date`` (default yesterday)."""
    if target_date_iso:
        from datetime import date as _date
        target = _date.fromisoformat(target_date_iso)
    else:
        target = (timezone.now() - timedelta(days=1)).date()

    processed = 0
    for student in User.objects.filter(role=User.Role.STUDENT, is_active=True).iterator():
        if not student.signal_sessions.filter(window_start__date=target).exists():
            continue
        rollup_day(student, target)
        processed += 1

    return {"date": target.isoformat(), "students_rolled_up": processed}
