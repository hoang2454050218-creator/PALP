from django.urls import path

from spacedrep import views

app_name = "spacedrep"

urlpatterns = [
    path("due/", views.DueItemsView.as_view(), name="due"),
    path("upcoming/", views.UpcomingItemsView.as_view(), name="upcoming"),
    path("review/", views.ReviewView.as_view(), name="review"),
]
