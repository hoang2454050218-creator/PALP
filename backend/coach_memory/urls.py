from django.urls import path

from coach_memory import views

app_name = "coach_memory"

urlpatterns = [
    path("me/", views.MyMemoryView.as_view(), name="me"),
]
