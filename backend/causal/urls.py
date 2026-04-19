from django.urls import path

from .views import CausalExperimentDetailView, CausalExperimentListView

app_name = "causal"

urlpatterns = [
    path("experiments/", CausalExperimentListView.as_view(), name="experiment-list"),
    path("experiments/<slug:name>/", CausalExperimentDetailView.as_view(), name="experiment-detail"),
]
