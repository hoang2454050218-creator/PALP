import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "palp.settings.development")

app = Celery("palp")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.update(
    worker_send_task_events=True,
    task_send_sent_event=True,
)


@app.on_after_configure.connect
def _setup_monitoring(sender, **kwargs):
    import analytics.monitoring  # noqa: F401
