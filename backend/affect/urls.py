from django.urls import path

from . import views

urlpatterns = [
    path("ingest/keystroke/", views.IngestKeystrokeView.as_view(), name="affect-ingest-ks"),
    path("ingest/linguistic/", views.IngestLinguisticView.as_view(), name="affect-ingest-text"),
    path("ingest/fused/", views.IngestFusedView.as_view(), name="affect-ingest-fused"),
    path("me/recent/", views.MyRecentAffectView.as_view(), name="affect-me-recent"),
]
