from django.urls import path

from knowledge_graph import views

app_name = "knowledge_graph"

urlpatterns = [
    path(
        "me/root-cause/<int:concept_id>/",
        views.MyRootCauseView.as_view(),
        name="me-root-cause",
    ),
    path(
        "student/<int:student_id>/root-cause/<int:concept_id>/",
        views.StudentRootCauseView.as_view(),
        name="student-root-cause",
    ),
    path("graph/", views.GraphExportView.as_view(), name="graph-export"),
]
