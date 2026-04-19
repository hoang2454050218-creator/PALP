from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CareerGoalView,
    NorthStarView,
    ReflectionSubmitView,
    SemesterGoalViewSet,
    StrategyPlanViewSet,
    TimeEstimateViewSet,
    TodayPlanView,
    WeeklyGoalViewSet,
)

app_name = "goals"

router = DefaultRouter()
router.register("semester", SemesterGoalViewSet, basename="semester-goal")
router.register("weekly", WeeklyGoalViewSet, basename="weekly-goal")
router.register("strategy-plan", StrategyPlanViewSet, basename="strategy-plan")
router.register("time-estimate", TimeEstimateViewSet, basename="time-estimate")

urlpatterns = [
    path("career/", CareerGoalView.as_view(), name="career"),
    path("today/", TodayPlanView.as_view(), name="today"),
    path("north-star/", NorthStarView.as_view(), name="north-star"),
    path("reflection/", ReflectionSubmitView.as_view(), name="reflection-submit"),
    path("", include(router.urls)),
]
