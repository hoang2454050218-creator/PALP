from django.urls import path
from analytics.health import LivenessView, ReadinessView, DeepHealthView

urlpatterns = [
    path("", LivenessView.as_view(), name="health-liveness"),
    path("ready/", ReadinessView.as_view(), name="health-readiness"),
    path("deep/", DeepHealthView.as_view(), name="health-deep"),
]
