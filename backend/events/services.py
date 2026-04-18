import logging

from django.utils import timezone

from .models import EventLog

logger = logging.getLogger("palp.audit")

VALID_EVENT_NAMES = frozenset(EventLog.EventName.values)


def audit_log(user, event_name: str, properties: dict | None = None, session_id: str = ""):
    """Persist an audit/event row, validating ``event_name`` against the
    canonical taxonomy so callers cannot silently drift the analytics schema.

    Raising at the call site is preferred over logging-and-continuing because
    a misnamed event will land in `palp_event_log` and pollute completeness/
    duplication audits forever - much easier to fix when the offending caller
    surfaces a 5xx in CI than to debug a "where did `gv_dashbord_view` come
    from?" data quality alert weeks later.
    """
    if event_name not in VALID_EVENT_NAMES:
        raise ValueError(
            f"Invalid event_name {event_name!r}. "
            f"Add it to events.models.EventLog.EventName before emitting."
        )

    actor_type = EventLog.ActorType.STUDENT
    if hasattr(user, "role"):
        actor_type = user.role

    entry = EventLog.objects.create(
        actor=user,
        actor_type=actor_type,
        event_name=event_name,
        timestamp_utc=timezone.now(),
        properties=properties or {},
        session_id=session_id,
    )
    logger.info(
        "audit event=%s user=%s props=%s",
        event_name, user.id, properties,
    )
    return entry
