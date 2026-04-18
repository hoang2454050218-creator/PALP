from django.conf import settings
from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.permissions import IsStudent, IsLecturerOrAdmin, IsStudentInLecturerClass
from curriculum.models import MicroTask, Milestone
from events.emitter import emit_event, confirm_event
from events.models import EventLog
from .models import MasteryState, TaskAttempt, ContentIntervention, StudentPathway
from curriculum.serializers import MicroTaskSerializer
from .serializers import (
    MasteryStateSerializer, TaskAttemptSerializer,
    ContentInterventionSerializer, StudentPathwaySerializer,
    SubmitTaskSerializer,
)
from .engine import update_mastery, decide_pathway_action
from palp.idempotency import idempotent
from palp.throttles import AssessmentSubmitThrottle

MASTERY_HIGH = settings.PALP_ADAPTIVE_THRESHOLDS["MASTERY_HIGH"]
MAX_DIFFICULTY = max(d[0] for d in MicroTask.DifficultyLevel.choices)
MIN_DIFFICULTY = min(d[0] for d in MicroTask.DifficultyLevel.choices)


class MyMasteryView(generics.ListAPIView):
    serializer_class = MasteryStateSerializer
    permission_classes = (IsStudent,)

    def get_queryset(self):
        qs = MasteryState.objects.filter(student=self.request.user).select_related("concept")
        course_id = self.request.query_params.get("course")
        if course_id:
            qs = qs.filter(concept__course_id=course_id)
        return qs


class SubmitTaskAttemptView(APIView):
    permission_classes = (IsStudent,)
    throttle_classes = (AssessmentSubmitThrottle,)

    @idempotent(required=True)
    @transaction.atomic
    def post(self, request):
        serializer = SubmitTaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        task = MicroTask.objects.select_related("concept", "concept__course").get(id=data["task_id"])

        prev_attempts = TaskAttempt.objects.filter(
            student=request.user, task=task
        ).count()

        mastery_before = MasteryState.objects.filter(
            student=request.user, concept=task.concept
        ).values_list("p_mastery", flat=True).first() or settings.PALP_BKT_DEFAULTS["P_L0"]

        is_correct = self._evaluate_task(task, data["answer"])
        score = task.max_score if is_correct else 0

        attempt = TaskAttempt.objects.create(
            student=request.user,
            task=task,
            score=score,
            max_score=task.max_score,
            duration_seconds=data["duration_seconds"],
            hints_used=data["hints_used"],
            is_correct=is_correct,
            answer=data["answer"],
            attempt_number=prev_attempts + 1,
        )

        mastery = update_mastery(request.user.id, task.concept_id, is_correct)
        pathway_action = decide_pathway_action(request.user.id, task.concept_id)

        self._update_pathway(request.user, task, mastery, pathway_action)

        event = emit_event(
            EventLog.EventName.MICRO_TASK_COMPLETED,
            actor=request.user,
            request_id=getattr(request, "request_id", None),
            course=task.concept.course,
            concept=task.concept,
            task=task,
            difficulty_level=task.difficulty,
            attempt_number=prev_attempts + 1,
            mastery_before=mastery_before,
            mastery_after=mastery.p_mastery,
            properties={
                "is_correct": is_correct,
                "score": score,
                "hints_used": data["hints_used"],
                "duration_seconds": data["duration_seconds"],
                "pathway_action": pathway_action.get("action"),
            },
            confirmed=True,
        )

        if not is_correct and prev_attempts >= settings.PALP_EARLY_WARNING["RETRY_FAILURE_THRESHOLD"] - 1:
            emit_event(
                EventLog.EventName.RETRY_TRIGGERED,
                actor=request.user,
                request_id=getattr(request, "request_id", None),
                course=task.concept.course,
                concept=task.concept,
                task=task,
                difficulty_level=task.difficulty,
                attempt_number=prev_attempts + 1,
                mastery_before=mastery_before,
                mastery_after=mastery.p_mastery,
                intervention_reason="retry_failure_threshold",
                confirmed=True,
            )

        return Response({
            "attempt": TaskAttemptSerializer(attempt).data,
            "mastery": MasteryStateSerializer(mastery).data,
            "pathway": pathway_action,
        })

    def _evaluate_task(self, task, answer):
        correct = task.content.get("correct_answer")
        if correct is None:
            return False
        if isinstance(correct, list):
            return answer == correct
        return str(answer) == str(correct)

    def _update_pathway(self, student, task, mastery, pathway_action):
        from curriculum.services import mark_task_completed, migrate_template_if_needed

        pathway, _ = StudentPathway.objects.select_for_update().get_or_create(
            student=student,
            course=task.concept.course,
            defaults={
                "current_concept": task.concept,
                "current_milestone": task.milestone,
            },
        )
        pathway.current_concept = task.concept
        pathway.current_milestone = task.milestone

        adjustment = pathway_action.get("difficulty_adjustment", 0)
        pathway.current_difficulty = max(
            MIN_DIFFICULTY, min(MAX_DIFFICULTY, pathway.current_difficulty + adjustment)
        )

        if task.milestone:
            migrate_template_if_needed(pathway, task.milestone)

        if mastery.p_mastery > MASTERY_HIGH:
            if task.concept_id not in (pathway.concepts_completed or []):
                completed = list(pathway.concepts_completed or [])
                completed.append(task.concept_id)
                pathway.concepts_completed = completed

            mark_task_completed(pathway, task.id)
        else:
            tasks_done = list(pathway.tasks_completed or [])
            if task.id not in tasks_done:
                tasks_done.append(task.id)
                pathway.tasks_completed = tasks_done

        self._check_milestone_completion(pathway, task.milestone)
        pathway.save()

    def _check_milestone_completion(self, pathway, milestone):
        if milestone is None or milestone.id in (pathway.milestones_completed or []):
            return

        all_task_ids = set(
            milestone.tasks.filter(is_active=True).values_list("id", flat=True)
        )
        if not all_task_ids:
            return

        completed_tasks = set(pathway.tasks_completed or [])
        if not all_task_ids.issubset(completed_tasks):
            return

        ms_done = list(pathway.milestones_completed or [])
        ms_done.append(milestone.id)
        pathway.milestones_completed = ms_done

        next_milestone = (
            Milestone.objects
            .filter(course=pathway.course, order__gt=milestone.order, is_active=True)
            .order_by("order")
            .first()
        )
        if next_milestone:
            pathway.current_milestone = next_milestone


class MyPathwayView(generics.RetrieveAPIView):
    serializer_class = StudentPathwaySerializer
    permission_classes = (IsStudent,)

    def get_object(self):
        from django.shortcuts import get_object_or_404
        from curriculum.models import Course

        course = get_object_or_404(Course, pk=self.kwargs["course_id"])
        pathway, _ = StudentPathway.objects.get_or_create(
            student=self.request.user,
            course=course,
        )
        return pathway


class MyTaskAttemptsView(generics.ListAPIView):
    serializer_class = TaskAttemptSerializer
    permission_classes = (IsStudent,)

    def get_queryset(self):
        qs = TaskAttempt.objects.filter(student=self.request.user).select_related("task")
        task_id = self.request.query_params.get("task")
        if task_id:
            qs = qs.filter(task_id=task_id)
        return qs[:50]


class MyInterventionsView(generics.ListAPIView):
    serializer_class = ContentInterventionSerializer
    permission_classes = (IsStudent,)

    def get_queryset(self):
        return ContentIntervention.objects.filter(
            student=self.request.user
        ).select_related("concept")[:20]


class NextTaskView(APIView):
    permission_classes = (IsStudent,)

    def get(self, request, course_id):
        pathway = StudentPathway.objects.filter(
            student=request.user, course_id=course_id
        ).select_related("current_concept", "current_milestone").first()

        if not pathway or not pathway.current_concept:
            return Response(
                {"detail": "Vui lòng hoàn thành đánh giá đầu vào trước."},
                status=status.HTTP_404_NOT_FOUND,
            )

        completed_task_ids = set(
            TaskAttempt.objects.filter(
                student=request.user, is_correct=True
            ).values_list("task_id", flat=True)
        )

        task = self._find_task(pathway, completed_task_ids)
        if not task:
            task = self._find_task_any_concept(pathway, completed_task_ids)

        if not task:
            return Response({"detail": "Hoàn thành tất cả bài tập!", "completed": True})

        return Response(MicroTaskSerializer(task).data)

    def _find_task(self, pathway, completed_task_ids):
        qs = MicroTask.objects.filter(
            concept=pathway.current_concept,
            is_active=True,
        ).exclude(id__in=completed_task_ids)

        exact = qs.filter(difficulty=pathway.current_difficulty).order_by("order").first()
        if exact:
            return exact

        return qs.order_by("difficulty", "order").first()

    def _find_task_any_concept(self, pathway, completed_task_ids):
        # Single query across every pending concept ordered by concept.order
        # then difficulty - O(1) round-trip instead of O(pending_concepts).
        pending_concept_ids = list(
            pathway.current_concept.course.concepts
            .filter(is_active=True)
            .exclude(id__in=pathway.concepts_completed)
            .values_list("id", flat=True)
            .order_by("order")
        )
        if not pending_concept_ids:
            return None
        return (
            MicroTask.objects
            .filter(concept_id__in=pending_concept_ids, is_active=True)
            .exclude(id__in=completed_task_ids)
            .order_by("concept__order", "difficulty", "order")
            .first()
        )


class StudentMasteryView(generics.ListAPIView):
    permission_classes = (IsLecturerOrAdmin, IsStudentInLecturerClass)

    def get_serializer_class(self):
        from .serializers import LecturerMasteryStateSerializer
        if self.request.user.is_lecturer:
            return LecturerMasteryStateSerializer
        return MasteryStateSerializer

    def get_queryset(self):
        return MasteryState.objects.filter(
            student_id=self.kwargs["student_id"]
        ).select_related("concept")
