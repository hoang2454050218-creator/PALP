from django.urls import path

from explainability import views

app_name = "explainability"

urlpatterns = [
    path("risk/me/", views.MyRiskExplanationView.as_view(), name="risk-me"),
    path(
        "risk/student/<int:student_id>/",
        views.StudentRiskExplanationView.as_view(),
        name="risk-student",
    ),
]
