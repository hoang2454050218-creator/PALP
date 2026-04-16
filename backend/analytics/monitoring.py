import time
import logging

from celery.signals import task_success, task_failure, task_retry
from django.core.cache import cache

logger = logging.getLogger("palp.celery")


@task_success.connect
def _on_task_success(sender=None, result=None, **kwargs):
    task_name = sender.name if sender else "unknown"
    runtime = getattr(sender.request, "runtime", None)

    cache.set(f"palp:task:last_success:{task_name}", time.time(), timeout=86400 * 7)

    _incr_counter(f"palp:task:count:success:{task_name}")

    logger.info(
        "Task succeeded: %s (runtime=%.2fs)",
        task_name,
        runtime or 0,
        extra={"task": task_name, "status": "success", "runtime": runtime},
    )


@task_failure.connect
def _on_task_failure(sender=None, exception=None, traceback=None, **kwargs):
    task_name = sender.name if sender else "unknown"

    _incr_counter(f"palp:task:count:failure:{task_name}")

    logger.error(
        "Task FAILED: %s — %s",
        task_name,
        exception,
        extra={"task": task_name, "status": "failure", "error": str(exception)},
        exc_info=True,
    )


@task_retry.connect
def _on_task_retry(sender=None, reason=None, **kwargs):
    task_name = sender.name if sender else "unknown"

    _incr_counter(f"palp:task:count:retry:{task_name}")

    logger.warning(
        "Task retrying: %s — %s",
        task_name,
        reason,
        extra={"task": task_name, "status": "retry", "reason": str(reason)},
    )


def _incr_counter(key: str):
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=86400 * 7)


def get_task_stats(task_name: str) -> dict:
    return {
        "successes": int(cache.get(f"palp:task:count:success:{task_name}") or 0),
        "failures": int(cache.get(f"palp:task:count:failure:{task_name}") or 0),
        "retries": int(cache.get(f"palp:task:count:retry:{task_name}") or 0),
        "last_success": cache.get(f"palp:task:last_success:{task_name}"),
    }
