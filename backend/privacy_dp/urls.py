from django.urls import path

from privacy_dp import views

app_name = "privacy_dp"

urlpatterns = [
    path("budgets/", views.BudgetListView.as_view(), name="budgets"),
    path("queries/", views.QueryLogView.as_view(), name="queries"),
]
