"""URL patterns for the Emergency Pipeline."""
from django.urls import path

from emergency import views

app_name = "emergency"

urlpatterns = [
    path("contact/", views.EmergencyContactView.as_view(), name="contact"),
    path("queue/", views.CounselorQueueView.as_view(), name="queue"),
    path(
        "events/<int:event_id>/",
        views.EmergencyEventDetailView.as_view(),
        name="event-detail",
    ),
    path(
        "events/<int:event_id>/acknowledge/",
        views.EmergencyAcknowledgeView.as_view(),
        name="event-ack",
    ),
    path(
        "events/<int:event_id>/resolve/",
        views.EmergencyResolveView.as_view(),
        name="event-resolve",
    ),
]
