from django.urls import path
from . import views

app_name = "events"

urlpatterns = [
    path("track/", views.TrackEventView.as_view(), name="track"),
    path("batch/", views.BatchTrackView.as_view(), name="batch-track"),
    path("my/", views.MyEventsView.as_view(), name="my-events"),
    path("student/<int:student_id>/", views.StudentEventsView.as_view(), name="student-events"),
]
