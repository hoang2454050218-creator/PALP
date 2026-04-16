import logging
from .models import EventLog

logger = logging.getLogger("palp.audit")


def audit_log(user, event_name: str, properties: dict | None = None, session_id: str = ""):
    entry = EventLog.objects.create(
        user=user,
        event_name=event_name,
        properties=properties or {},
        session_id=session_id,
    )
    logger.info(
        "audit event=%s user=%s props=%s",
        event_name, user.id, properties,
    )
    return entry
