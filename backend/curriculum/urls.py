from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"tasks", views.MicroTaskViewSet, basename="microtask")

app_name = "curriculum"

urlpatterns = [
    path("courses/", views.CourseListView.as_view(), name="course-list"),
    path("courses/<int:pk>/", views.CourseDetailView.as_view(), name="course-detail"),
    path("courses/<int:course_id>/concepts/", views.ConceptListView.as_view(), name="concept-list"),
    path("courses/<int:course_id>/milestones/", views.MilestoneListView.as_view(), name="milestone-list"),
    path("milestones/<int:pk>/", views.MilestoneDetailView.as_view(), name="milestone-detail"),
    path("concepts/<int:concept_id>/content/", views.SupplementaryContentListView.as_view(), name="supplementary-list"),
    path("my-enrollments/", views.MyEnrollmentsView.as_view(), name="my-enrollments"),
    path("", include(router.urls)),
]
