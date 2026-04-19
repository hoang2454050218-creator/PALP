"""HTTP endpoints for the DKT app.

| Method | Path                                       | Auth                       |
| ------ | ------------------------------------------ | -------------------------- |
| GET    | ``me/``                                    | IsStudent (own)            |
| GET    | ``student/<id>/``                          | IsLecturerOfStudent        |
| POST   | ``predict/``                               | IsStudent (own)            |
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import (
    IsLecturer,
    IsStudent,
    IsStudentInLecturerClass,
)

from dkt.serializers import DKTPredictionSerializer
from dkt.services import (
    predict_for_concept,
    predict_for_student,
)


class MyDKTPredictionsView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        top_k = int(request.query_params.get("top_k", 10))
        results = predict_for_student(student=request.user, top_k=top_k)
        return Response(
            {
                "predictions": DKTPredictionSerializer(
                    [r.persisted for r in results], many=True,
                ).data
            }
        )


class StudentDKTPredictionsView(APIView):
    permission_classes = [
        IsAuthenticated, IsLecturer, IsStudentInLecturerClass,
    ]

    def get(self, request, student_id):
        from accounts.models import User

        student = User.objects.filter(id=student_id, role=User.Role.STUDENT).first()
        if not student:
            return Response(
                {"detail": "Không tìm thấy sinh viên."},
                status=status.HTTP_404_NOT_FOUND,
            )
        top_k = int(request.query_params.get("top_k", 10))
        results = predict_for_student(student=student, top_k=top_k)
        return Response(
            {
                "predictions": DKTPredictionSerializer(
                    [r.persisted for r in results], many=True,
                ).data
            }
        )


class DKTPredictView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def post(self, request):
        concept_id = request.data.get("concept_id")
        if not concept_id:
            return Response(
                {"detail": "concept_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            concept_id_int = int(concept_id)
        except (TypeError, ValueError):
            return Response(
                {"detail": "concept_id must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = predict_for_concept(
            student=request.user, target_concept_id=concept_id_int,
        )
        return Response(DKTPredictionSerializer(result.persisted).data)
