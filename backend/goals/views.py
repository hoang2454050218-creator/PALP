"""
HTTP layer for the Direction Engine.

Endpoints:
  /api/goals/career/                CRUD on CareerGoal (1 per student)
  /api/goals/semester/              CRUD on SemesterGoal
  /api/goals/weekly/                CRUD on WeeklyGoal
  /api/goals/today/                 daily plan (read-only, derived)
  /api/goals/north-star/            aggregated panel data
  /api/goals/reflection/            POST submit reflection
  /api/goals/strategy-plan/         CRUD on StrategyPlan
  /api/goals/time-estimate/         CRUD on TimeEstimate
"""
from __future__ import annotations

from rest_framework import generics, mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsStudent

from .models import (
    CareerGoal,
    EffortRating,
    GoalReflection,
    SemesterGoal,
    StrategyPlan,
    TimeEstimate,
    WeeklyGoal,
)
from .reflection import ReflectionSubmission, submit_reflection
from .serializers import (
    CareerGoalSerializer,
    EffortRatingSerializer,
    GoalReflectionSerializer,
    ReflectionSubmitSerializer,
    SemesterGoalSerializer,
    StrategyPlanSerializer,
    TimeEstimateSerializer,
    WeeklyGoalSerializer,
)
from .services import generate_daily_plan, get_active_semester_goals, get_active_weekly_goal


class CareerGoalView(APIView):
    """OneToOne so we can reuse a single retrieve/upsert endpoint."""

    permission_classes = (IsAuthenticated, IsStudent)

    def get(self, request):
        obj = CareerGoal.objects.filter(student=request.user).first()
        if obj is None:
            return Response({"detail": "No career goal yet."}, status=status.HTTP_204_NO_CONTENT)
        return Response(CareerGoalSerializer(obj).data)

    def put(self, request):
        serializer = CareerGoalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj, _ = CareerGoal.objects.update_or_create(
            student=request.user,
            defaults=serializer.validated_data,
        )
        return Response(CareerGoalSerializer(obj).data, status=status.HTTP_200_OK)

    def delete(self, request):
        CareerGoal.objects.filter(student=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SemesterGoalViewSet(viewsets.ModelViewSet):
    serializer_class = SemesterGoalSerializer
    permission_classes = (IsAuthenticated, IsStudent)

    def get_queryset(self):
        return SemesterGoal.objects.filter(student=self.request.user).select_related("course")

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)


class WeeklyGoalViewSet(viewsets.ModelViewSet):
    serializer_class = WeeklyGoalSerializer
    permission_classes = (IsAuthenticated, IsStudent)

    def get_queryset(self):
        return WeeklyGoal.objects.filter(student=self.request.user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)
        # best-effort emit
        try:
            from events.emitter import emit_event
            from events.models import EventLog
            obj = serializer.instance
            emit_event(
                EventLog.EventName.GOAL_SET,
                actor=self.request.user,
                actor_type=EventLog.ActorType.STUDENT,
                properties={
                    "goal_type": "weekly",
                    "goal_id": obj.id,
                    "target_minutes": obj.target_minutes,
                    "target_concepts": obj.target_concept_ids,
                },
            )
        except Exception:  # pragma: no cover - non-fatal
            pass


class StrategyPlanViewSet(viewsets.ModelViewSet):
    serializer_class = StrategyPlanSerializer
    permission_classes = (IsAuthenticated, IsStudent)

    def get_queryset(self):
        return StrategyPlan.objects.filter(weekly_goal__student=self.request.user)

    def perform_create(self, serializer):
        weekly = serializer.validated_data["weekly_goal"]
        if weekly.student_id != self.request.user.id:
            raise PermissionError("Cannot attach strategy to another student's weekly goal.")
        obj = serializer.save()
        try:
            from events.emitter import emit_event
            from events.models import EventLog
            emit_event(
                EventLog.EventName.STRATEGY_PLAN_SET,
                actor=self.request.user,
                actor_type=EventLog.ActorType.STUDENT,
                properties={
                    "weekly_goal_id": weekly.id,
                    "strategy_label": obj.strategy,
                    "predicted_minutes": obj.predicted_minutes,
                },
            )
        except Exception:  # pragma: no cover
            pass


class TimeEstimateViewSet(viewsets.ModelViewSet):
    serializer_class = TimeEstimateSerializer
    permission_classes = (IsAuthenticated, IsStudent)

    def get_queryset(self):
        return TimeEstimate.objects.filter(student=self.request.user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)


class TodayPlanView(APIView):
    permission_classes = (IsAuthenticated, IsStudent)

    def get(self, request):
        plan = generate_daily_plan(request.user)
        return Response({
            "date": plan.date,
            "weekly_goal_id": plan.weekly_goal_id,
            "items": [
                {
                    "kind": item.kind,
                    "title": item.title,
                    "rationale": item.rationale,
                    "micro_task_id": item.micro_task_id,
                    "concept_id": item.concept_id,
                    "estimated_minutes": item.estimated_minutes,
                }
                for item in plan.items
            ],
        })


class NorthStarView(APIView):
    """Aggregated payload for the 3-panel North Star UI.

    Forethought:    career goal + active semester goals + active weekly goal
    Performance:    last 7 days actual focus / completion derived from signals + adaptive
    Self-Reflection: latest GoalReflection (if any) + drift snapshot
    """

    permission_classes = (IsAuthenticated, IsStudent)

    def get(self, request):
        career = CareerGoal.objects.filter(student=request.user).first()
        semester = list(get_active_semester_goals(request.user))
        weekly = get_active_weekly_goal(request.user)

        latest_reflection = (
            GoalReflection.objects.filter(student=request.user)
            .order_by("-week_start").first()
        )

        return Response({
            "forethought": {
                "career_goal": CareerGoalSerializer(career).data if career else None,
                "semester_goals": SemesterGoalSerializer(semester, many=True).data,
                "weekly_goal": WeeklyGoalSerializer(weekly).data if weekly else None,
            },
            "performance": {
                "weekly_goal": WeeklyGoalSerializer(weekly).data if weekly else None,
                "drift_pct_last_check": (
                    weekly.drift_pct_last_check if weekly else None
                ),
            },
            "reflection": {
                "latest": GoalReflectionSerializer(latest_reflection).data if latest_reflection else None,
            },
        })


class ReflectionSubmitView(APIView):
    permission_classes = (IsAuthenticated, IsStudent)

    def post(self, request):
        serializer = ReflectionSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            obj = submit_reflection(
                student=request.user,
                payload=ReflectionSubmission(
                    weekly_goal_id=data["weekly_goal_id"],
                    learned_text=data.get("learned_text", ""),
                    struggle_text=data.get("struggle_text", ""),
                    next_priority_text=data.get("next_priority_text", ""),
                    effort_rating=data.get("effort_rating"),
                    effort_note=data.get("effort_note", ""),
                    strategy_effectiveness=data.get("strategy_effectiveness") or {},
                ),
            )
        except WeeklyGoal.DoesNotExist:
            return Response({"detail": "weekly_goal_id not found for this student."}, status=404)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)

        return Response(GoalReflectionSerializer(obj).data, status=status.HTTP_201_CREATED)
