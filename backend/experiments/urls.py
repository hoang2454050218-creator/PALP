from django.urls import path

from . import views

urlpatterns = [
    path(
        "my-assignments/",
        views.MyAssignmentsView.as_view(),
        name="experiments-my-assignments",
    ),
    path(
        "<slug:name>/results/",
        views.ExperimentResultsView.as_view(),
        name="experiments-results",
    ),
]
