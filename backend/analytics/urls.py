from django.urls import path
from . import views

app_name = "analytics"

urlpatterns = [
    path("kpi/<int:class_id>/", views.KPISnapshotView.as_view(), name="kpi-snapshot"),
    path("kpi-registry/", views.KPIRegistryView.as_view(), name="kpi-registry"),
    path("kpi-registry/<str:code>/", views.KPIRegistryDetailView.as_view(), name="kpi-registry-detail"),
    path("kpi-lineage/", views.KPILineageListView.as_view(), name="kpi-lineage"),
    path("reports/", views.PilotReportListView.as_view(), name="report-list"),
    path("reports/<int:pk>/", views.PilotReportDetailView.as_view(), name="report-detail"),
    path("data-quality/", views.DataQualityListView.as_view(), name="data-quality"),
]
