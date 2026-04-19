from django.urls import path

from dkt import views

app_name = "dkt"

urlpatterns = [
    path("me/", views.MyDKTPredictionsView.as_view(), name="me"),
    path(
        "student/<int:student_id>/",
        views.StudentDKTPredictionsView.as_view(),
        name="student",
    ),
    path("predict/", views.DKTPredictView.as_view(), name="predict"),
]
