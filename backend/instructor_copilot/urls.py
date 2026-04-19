from django.urls import path

from instructor_copilot import views

app_name = "instructor_copilot"

urlpatterns = [
    path(
        "exercises/generate/",
        views.GenerateExerciseView.as_view(),
        name="exercises-generate",
    ),
    path("exercises/", views.ListExercisesView.as_view(), name="exercises-list"),
    path(
        "exercises/<int:exercise_id>/approve/",
        views.ApproveExerciseView.as_view(),
        name="exercises-approve",
    ),
    path(
        "exercises/<int:exercise_id>/reject/",
        views.RejectExerciseView.as_view(),
        name="exercises-reject",
    ),
    path(
        "feedback/draft/",
        views.DraftFeedbackView.as_view(),
        name="feedback-draft",
    ),
    path("feedback/", views.ListFeedbackView.as_view(), name="feedback-list"),
]
