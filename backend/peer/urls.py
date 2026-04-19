"""URL patterns for the Peer Engine."""
from django.urls import path

from peer import views

app_name = "peer"

urlpatterns = [
    path("consent/", views.PeerConsentView.as_view(), name="consent"),
    path("frontier/", views.FrontierView.as_view(), name="frontier"),
    path("benchmark/", views.BenchmarkView.as_view(), name="benchmark"),
    path("buddy/find/", views.BuddyFindView.as_view(), name="buddy-find"),
    path("buddy/me/", views.BuddyMineView.as_view(), name="buddy-me"),
    path(
        "buddy/<int:match_id>/respond/",
        views.BuddyRespondView.as_view(),
        name="buddy-respond",
    ),
    path(
        "teaching-session/<int:match_id>/start/",
        views.TeachingSessionStartView.as_view(),
        name="teaching-session-start",
    ),
    path(
        "herd-clusters/",
        views.HerdClusterListView.as_view(),
        name="herd-clusters",
    ),
    path(
        "herd-clusters/<int:cluster_id>/review/",
        views.HerdClusterReviewView.as_view(),
        name="herd-cluster-review",
    ),
]
