from django.urls import path

from .views import FairnessAuditDetailView, FairnessAuditListView

app_name = "fairness"

urlpatterns = [
    path("audits/", FairnessAuditListView.as_view(), name="audit-list"),
    path("audits/<int:pk>/", FairnessAuditDetailView.as_view(), name="audit-detail"),
]
