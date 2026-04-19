from django.urls import path

from .views import MySignalsView, SignalIngestView

app_name = "signals"

urlpatterns = [
    path("ingest/", SignalIngestView.as_view(), name="ingest"),
    path("my/", MySignalsView.as_view(), name="my-sessions"),
]
