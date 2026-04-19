"""HTTP endpoints for the Instructor Co-pilot.

| Method | Path                                          | Auth                |
| ------ | --------------------------------------------- | ------------------- |
| POST   | ``exercises/generate/``                        | IsLecturer          |
| GET    | ``exercises/``                                 | IsLecturer          |
| POST   | ``exercises/<id>/approve/``                    | IsLecturer          |
| POST   | ``exercises/<id>/reject/``                     | IsLecturer          |
| POST   | ``feedback/draft/``                            | IsLecturer          |
| GET    | ``feedback/``                                  | IsLecturer          |
"""
from __future__ import annotations

from datetime import date

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsLecturer

from instructor_copilot.models import FeedbackDraft, GeneratedExercise
from instructor_copilot.services import (
    approve_exercise,
    draft_feedback,
    generate_exercise,
)


def _serialize_exercise(ex: GeneratedExercise) -> dict:
    return {
        "id": ex.id,
        "course_id": ex.course_id,
        "concept_id": ex.concept_id,
        "concept_name": ex.concept.name,
        "template_key": ex.template_key,
        "difficulty": ex.difficulty,
        "title": ex.title,
        "body": ex.body,
        "status": ex.status,
        "review_notes": ex.review_notes,
        "published_micro_task_id": ex.published_micro_task_id,
        "created_at": ex.created_at.isoformat(),
        "updated_at": ex.updated_at.isoformat(),
    }


def _serialize_feedback(fb: FeedbackDraft) -> dict:
    return {
        "id": fb.id,
        "student_id": fb.student_id,
        "week_start": fb.week_start.isoformat(),
        "summary": fb.summary,
        "highlights": fb.highlights,
        "concerns": fb.concerns,
        "suggestions": fb.suggestions,
        "status": fb.status,
        "sent_at": fb.sent_at.isoformat() if fb.sent_at else None,
        "created_at": fb.created_at.isoformat(),
        "updated_at": fb.updated_at.isoformat(),
    }


class GenerateExerciseView(APIView):
    permission_classes = [IsAuthenticated, IsLecturer]

    def post(self, request):
        from curriculum.models import Concept, Course

        course_id = request.data.get("course_id")
        concept_id = request.data.get("concept_id")
        difficulty = request.data.get("difficulty", 2)
        if not course_id or not concept_id:
            return Response(
                {"detail": "course_id + concept_id are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            difficulty_int = int(difficulty)
        except (TypeError, ValueError):
            return Response(
                {"detail": "difficulty must be 1..3."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        course = Course.objects.filter(pk=course_id, is_active=True).first()
        concept = Concept.objects.filter(
            pk=concept_id, course=course, is_active=True,
        ).first()
        if not course or not concept:
            return Response(
                {"detail": "Không tìm thấy course / concept."},
                status=status.HTTP_404_NOT_FOUND,
            )

        ex = generate_exercise(
            course=course, concept=concept,
            requested_by=request.user, difficulty=difficulty_int,
        )
        return Response(_serialize_exercise(ex), status=status.HTTP_201_CREATED)


class ListExercisesView(APIView):
    permission_classes = [IsAuthenticated, IsLecturer]

    def get(self, request):
        course_id = request.query_params.get("course_id")
        qs = (
            GeneratedExercise.objects
            .filter(requested_by=request.user)
            .select_related("concept")
        )
        if course_id:
            qs = qs.filter(course_id=course_id)
        qs = qs.order_by("-created_at")[:50]
        return Response(
            {"exercises": [_serialize_exercise(e) for e in qs]}
        )


class ApproveExerciseView(APIView):
    permission_classes = [IsAuthenticated, IsLecturer]

    def post(self, request, exercise_id):
        ex = (
            GeneratedExercise.objects
            .filter(pk=exercise_id, requested_by=request.user)
            .first()
        )
        if not ex:
            return Response(
                {"detail": "Không tìm thấy exercise."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            approve_exercise(
                exercise=ex,
                reviewer=request.user,
                notes=request.data.get("notes", ""),
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )
        ex.refresh_from_db()
        return Response(_serialize_exercise(ex))


class RejectExerciseView(APIView):
    permission_classes = [IsAuthenticated, IsLecturer]

    def post(self, request, exercise_id):
        ex = (
            GeneratedExercise.objects
            .filter(pk=exercise_id, requested_by=request.user)
            .first()
        )
        if not ex:
            return Response(
                {"detail": "Không tìm thấy exercise."},
                status=status.HTTP_404_NOT_FOUND,
            )
        ex.status = GeneratedExercise.Status.REJECTED
        ex.review_notes = (ex.review_notes + "\n" + request.data.get("notes", "")).strip()
        ex.save(update_fields=["status", "review_notes", "updated_at"])
        return Response(_serialize_exercise(ex))


class DraftFeedbackView(APIView):
    permission_classes = [IsAuthenticated, IsLecturer]

    def post(self, request):
        from accounts.models import User

        student_id = request.data.get("student_id")
        week_start_str = request.data.get("week_start")
        if not student_id or not week_start_str:
            return Response(
                {"detail": "student_id + week_start are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            week_start = date.fromisoformat(week_start_str)
        except ValueError:
            return Response(
                {"detail": "week_start must be ISO date (YYYY-MM-DD)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        student = User.objects.filter(id=student_id, role=User.Role.STUDENT).first()
        if not student:
            return Response(
                {"detail": "Không tìm thấy sinh viên."},
                status=status.HTTP_404_NOT_FOUND,
            )

        draft = draft_feedback(
            student=student, requested_by=request.user, week_start=week_start,
        )
        return Response(_serialize_feedback(draft), status=status.HTTP_201_CREATED)


class ListFeedbackView(APIView):
    permission_classes = [IsAuthenticated, IsLecturer]

    def get(self, request):
        qs = (
            FeedbackDraft.objects
            .filter(requested_by=request.user)
            .order_by("-created_at")[:50]
        )
        return Response(
            {"drafts": [_serialize_feedback(d) for d in qs]}
        )
