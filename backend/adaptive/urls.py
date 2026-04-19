from django.urls import path
from . import views
from .calibration_views import CalibrationRecordView, MyCalibrationView

app_name = "adaptive"

urlpatterns = [
    path("mastery/", views.MyMasteryView.as_view(), name="my-mastery"),
    path("submit/", views.SubmitTaskAttemptView.as_view(), name="submit-task"),
    path("pathway/<int:course_id>/", views.MyPathwayView.as_view(), name="my-pathway"),
    path("next-task/<int:course_id>/", views.NextTaskView.as_view(), name="next-task"),
    path("attempts/", views.MyTaskAttemptsView.as_view(), name="my-attempts"),
    path("interventions/", views.MyInterventionsView.as_view(), name="my-interventions"),
    path("student/<int:student_id>/mastery/", views.StudentMasteryView.as_view(), name="student-mastery"),
    # Phase 1E — Metacognitive calibration
    path("calibration/", CalibrationRecordView.as_view(), name="calibration-record"),
    path("calibration/me/", MyCalibrationView.as_view(), name="calibration-me"),
]
