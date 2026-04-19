from django.urls import path

from bandit import views

app_name = "bandit"

urlpatterns = [
    path("select/", views.BanditSelectView.as_view(), name="select"),
    path(
        "decisions/<int:decision_id>/reward/",
        views.BanditRewardView.as_view(),
        name="reward",
    ),
    path(
        "experiments/<slug:experiment_key>/stats/",
        views.BanditStatsView.as_view(),
        name="stats",
    ),
]
