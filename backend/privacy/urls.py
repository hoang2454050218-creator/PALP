from django.urls import path
from . import views

app_name = "privacy"

urlpatterns = [
    path("consent/", views.ConsentStatusView.as_view(), name="consent"),
    path("consent/history/", views.ConsentHistoryView.as_view(), name="consent-history"),
    path("export/", views.DataExportView.as_view(), name="export"),
    path("delete/", views.DataDeleteView.as_view(), name="delete"),
    path("delete/requests/", views.DeletionRequestListView.as_view(), name="deletion-requests"),
    path("audit-log/", views.AuditLogView.as_view(), name="audit-log"),
    path("incidents/", views.PrivacyIncidentView.as_view(), name="incidents"),
]
