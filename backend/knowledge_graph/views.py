"""HTTP endpoints for the Knowledge Graph + root-cause analyzer.

| Method | Path                                              | Auth                |
| ------ | ------------------------------------------------- | ------------------- |
| GET    | ``me/root-cause/<concept_id>/``                   | IsStudent (own)     |
| GET    | ``student/<sid>/root-cause/<concept_id>/``        | IsLecturerOfStudent |
| GET    | ``graph/``                                        | IsLecturerOrAdmin   |
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import (
    IsLecturer,
    IsLecturerOrAdmin,
    IsStudent,
    IsStudentInLecturerClass,
)

from knowledge_graph.services import (
    cache_snapshot,
    export_graph,
    find_root_cause,
)


def _serialize_snapshot(snap) -> dict:
    return {
        "target_concept_id": snap.target_concept_id,
        "weakest_prerequisite_id": snap.weakest_prerequisite_id,
        "walk": snap.walk_payload,
        "confidence": snap.confidence,
        "computed_at": snap.computed_at,
    }


class MyRootCauseView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request, concept_id):
        from curriculum.models import Concept

        target = Concept.objects.filter(pk=concept_id, is_active=True).first()
        if not target:
            return Response(
                {"detail": "Không tìm thấy concept."},
                status=status.HTTP_404_NOT_FOUND,
            )
        snap = cache_snapshot(student=request.user, target_concept=target)
        return Response(_serialize_snapshot(snap))


class StudentRootCauseView(APIView):
    permission_classes = [
        IsAuthenticated, IsLecturer, IsStudentInLecturerClass,
    ]

    def get(self, request, student_id, concept_id):
        from accounts.models import User
        from curriculum.models import Concept

        student = User.objects.filter(id=student_id, role=User.Role.STUDENT).first()
        if not student:
            return Response(
                {"detail": "Không tìm thấy sinh viên."},
                status=status.HTTP_404_NOT_FOUND,
            )
        target = Concept.objects.filter(pk=concept_id, is_active=True).first()
        if not target:
            return Response(
                {"detail": "Không tìm thấy concept."},
                status=status.HTTP_404_NOT_FOUND,
            )
        snap = cache_snapshot(student=student, target_concept=target)
        return Response(_serialize_snapshot(snap))


class GraphExportView(APIView):
    permission_classes = [IsAuthenticated, IsLecturerOrAdmin]

    def get(self, request):
        return Response(export_graph())
