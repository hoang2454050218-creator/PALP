from django.urls import path

from .views import CanonicalLookupView, LinkSessionView

app_name = "device_sessions"

urlpatterns = [
    path("link/", LinkSessionView.as_view(), name="link"),
    path("canonical/", CanonicalLookupView.as_view(), name="canonical-lookup"),
]
