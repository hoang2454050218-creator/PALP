"""URL patterns for the AI Coach."""
from django.urls import path

from coach import views

app_name = "coach"

urlpatterns = [
    path("consent/", views.CoachConsentView.as_view(), name="consent"),
    path("message/", views.CoachMessageView.as_view(), name="message"),
    path(
        "conversations/",
        views.CoachConversationListView.as_view(),
        name="conversation-list",
    ),
    path(
        "conversations/<int:conversation_id>/",
        views.CoachConversationDetailView.as_view(),
        name="conversation-detail",
    ),
    path(
        "conversations/<int:conversation_id>/end/",
        views.CoachConversationEndView.as_view(),
        name="conversation-end",
    ),
]
