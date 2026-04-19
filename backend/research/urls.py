from django.urls import path

from . import views

urlpatterns = [
    path("protocols/", views.ResearchProtocolListView.as_view(), name="research-protocols"),
    path("protocols/<slug:code>/", views.ResearchProtocolDetailView.as_view(), name="research-protocol-detail"),
    path("protocols/<slug:code>/opt-in/", views.ResearchOptInView.as_view(), name="research-opt-in"),
    path("protocols/<slug:code>/withdraw/", views.ResearchWithdrawView.as_view(), name="research-withdraw"),
    path("protocols/<slug:code>/decline/", views.ResearchDeclineView.as_view(), name="research-decline"),
    path("me/participations/", views.MyResearchParticipationListView.as_view(), name="research-mine"),
    path("exports/", views.AnonymizedExportListView.as_view(), name="research-exports"),
]
