from django.urls import path

from . import views

urlpatterns = [
    path("model-cards/", views.ModelCardListView.as_view(), name="pub-model-cards"),
    path("model-cards/<int:id>/", views.ModelCardDetailView.as_view(), name="pub-model-card-detail"),
    path("model-cards/draft/", views.ModelCardDraftView.as_view(), name="pub-model-card-draft"),
    path("model-cards/<int:id>/promote/", views.ModelCardPromoteView.as_view(), name="pub-model-card-promote"),
    path("datasheets/", views.DatasheetListView.as_view(), name="pub-datasheets"),
    path("datasheets/draft/", views.DatasheetDraftView.as_view(), name="pub-datasheet-draft"),
    path("repro-kits/", views.ReproKitListView.as_view(), name="pub-repro-kits"),
    path("repro-kits/create/", views.ReproKitCreateView.as_view(), name="pub-repro-kit-create"),
]
