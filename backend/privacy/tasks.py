import logging

from celery import shared_task

logger = logging.getLogger("palp.privacy")


@shared_task(name="privacy.enforce_retention")
def enforce_retention_task():
    from .services import enforce_retention
    total = enforce_retention()
    logger.info("Retention enforcement completed: %d records affected", total)
    return {"records_affected": total}


@shared_task(name="privacy.check_incident_sla")
def check_incident_sla_task():
    from django.utils import timezone
    from .models import PrivacyIncident

    overdue = PrivacyIncident.objects.filter(
        status__in=[
            PrivacyIncident.Status.OPEN,
            PrivacyIncident.Status.INVESTIGATING,
        ],
        sla_deadline__lt=timezone.now(),
    )

    count = overdue.count()
    if count > 0:
        logger.warning(
            "SLA BREACH: %d privacy incidents overdue (48h SLA exceeded)", count
        )

        for incident in overdue:
            logger.warning(
                "Overdue incident #%d: [%s] %s (created %s, deadline %s)",
                incident.id,
                incident.severity,
                incident.title,
                incident.created_at.isoformat(),
                incident.sla_deadline.isoformat(),
            )

    return {"overdue_count": count}
