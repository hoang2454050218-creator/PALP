from django.urls import path

from .views import MyRiskScoreView, StudentRiskHistoryView, StudentRiskScoreView

app_name = "risk"

urlpatterns = [
    path("me/", MyRiskScoreView.as_view(), name="my-risk"),
    path("student/<int:student_id>/", StudentRiskScoreView.as_view(), name="student-risk"),
    path("student/<int:student_id>/history/", StudentRiskHistoryView.as_view(), name="student-risk-history"),
]
