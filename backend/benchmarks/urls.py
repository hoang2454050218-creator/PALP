from django.urls import path

from . import views

urlpatterns = [
    path("datasets/", views.BenchmarkDatasetListView.as_view(), name="benchmarks-datasets"),
    path("predictors/", views.BenchmarkPredictorListView.as_view(), name="benchmarks-predictors"),
    path("runs/", views.BenchmarkRunListView.as_view(), name="benchmarks-runs"),
    path("runs/<int:id>/", views.BenchmarkRunDetailView.as_view(), name="benchmarks-run-detail"),
    path("run/", views.BenchmarkRunTriggerView.as_view(), name="benchmarks-run-trigger"),
]
