from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("class/<int:class_id>/overview/", views.ClassOverviewView.as_view(), name="class-overview"),
    path("alerts/", views.AlertListView.as_view(), name="alert-list"),
    path("alerts/<int:pk>/dismiss/", views.DismissAlertView.as_view(), name="dismiss-alert"),
    path("interventions/", views.CreateInterventionView.as_view(), name="create-intervention"),
    path("interventions/history/", views.InterventionHistoryView.as_view(), name="intervention-history"),
    path("interventions/<int:pk>/follow-up/", views.UpdateFollowUpView.as_view(), name="update-follow-up"),
]
