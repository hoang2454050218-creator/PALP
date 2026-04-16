from django.urls import path
from . import views

app_name = "assessment"

urlpatterns = [
    path("", views.AssessmentListView.as_view(), name="list"),
    path("<int:pk>/questions/", views.AssessmentQuestionsView.as_view(), name="questions"),
    path("<int:pk>/start/", views.StartAssessmentView.as_view(), name="start"),
    path("sessions/<int:session_id>/answer/", views.SubmitAnswerView.as_view(), name="submit-answer"),
    path("sessions/<int:session_id>/complete/", views.CompleteAssessmentView.as_view(), name="complete"),
    path("my-sessions/", views.MyAssessmentSessionsView.as_view(), name="my-sessions"),
    path("profile/<int:course_id>/", views.LearnerProfileView.as_view(), name="my-profile"),
    path("profile/<int:course_id>/student/<int:student_id>/", views.StudentLearnerProfileView.as_view(), name="student-profile"),
]
