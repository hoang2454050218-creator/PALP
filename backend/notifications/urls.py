"""URL patterns for the Notifications app."""
from django.urls import path

from notifications import views

app_name = "notifications"

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="list"),
    path("unread-count/", views.UnreadCountView.as_view(), name="unread-count"),
    path("mark-read/", views.MarkReadView.as_view(), name="mark-read"),
    path("<int:notification_id>/read/", views.MarkOneReadView.as_view(), name="mark-one-read"),
    path("preference/", views.PreferenceView.as_view(), name="preference"),
]
