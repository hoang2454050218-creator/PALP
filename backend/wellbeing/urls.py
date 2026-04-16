from django.urls import path
from . import views

app_name = "wellbeing"

urlpatterns = [
    path("check/", views.CheckWellbeingView.as_view(), name="check"),
    path("nudge/<int:pk>/respond/", views.NudgeResponseView.as_view(), name="nudge-respond"),
    path("my/", views.MyNudgesView.as_view(), name="my-nudges"),
]
