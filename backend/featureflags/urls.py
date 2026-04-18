from django.urls import path

from . import views

urlpatterns = [
    path("active/", views.ActiveFlagsView.as_view(), name="featureflags-active"),
]
