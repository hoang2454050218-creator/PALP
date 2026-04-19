from django.urls import path

from .views import (
    DriftReportListView,
    ModelRegistryListView,
    ModelVersionListView,
    ShadowComparisonListView,
)

app_name = "mlops"

urlpatterns = [
    path("models/", ModelRegistryListView.as_view(), name="model-list"),
    path("models/<slug:name>/versions/", ModelVersionListView.as_view(), name="model-versions"),
    path("models/<slug:name>/drift/", DriftReportListView.as_view(), name="model-drift"),
    path("models/<slug:name>/shadow/", ShadowComparisonListView.as_view(), name="model-shadow"),
]
