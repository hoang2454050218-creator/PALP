from django.db.models import Avg
from django.shortcuts import get_object_or_404
from rest_framework import generics, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsLecturerOrAdmin

from .models import Course, Enrollment, Concept, ConceptPrerequisite, Milestone, MicroTask, SupplementaryContent
from .serializers import (
    CourseSerializer, EnrollmentSerializer, ConceptSerializer,
    MilestoneSerializer, MilestoneListSerializer,
    MicroTaskSerializer, SupplementaryContentSerializer,
)


class CourseListView(generics.ListAPIView):
    queryset = Course.objects.filter(is_active=True)
    serializer_class = CourseSerializer


class CourseDetailView(generics.RetrieveAPIView):
    queryset = Course.objects.filter(is_active=True)
    serializer_class = CourseSerializer


class ConceptListView(generics.ListAPIView):
    serializer_class = ConceptSerializer

    def get_queryset(self):
        return Concept.objects.filter(
            course_id=self.kwargs["course_id"], is_active=True
        ).prefetch_related("prerequisites")


class MilestoneListView(generics.ListAPIView):
    serializer_class = MilestoneListSerializer

    def get_queryset(self):
        return Milestone.objects.filter(
            course_id=self.kwargs["course_id"], is_active=True
        )


class MilestoneDetailView(generics.RetrieveAPIView):
    serializer_class = MilestoneSerializer

    def get_queryset(self):
        return Milestone.objects.filter(is_active=True).prefetch_related("tasks", "concepts")


class MicroTaskViewSet(viewsets.ModelViewSet):
    serializer_class = MicroTaskSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsLecturerOrAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = MicroTask.objects.filter(is_active=True).select_related("concept")
        milestone_id = self.request.query_params.get("milestone")
        if milestone_id:
            qs = qs.filter(milestone_id=milestone_id)
        concept_id = self.request.query_params.get("concept")
        if concept_id:
            qs = qs.filter(concept_id=concept_id)
        return qs


class SupplementaryContentListView(generics.ListAPIView):
    serializer_class = SupplementaryContentSerializer

    def get_queryset(self):
        return SupplementaryContent.objects.filter(concept_id=self.kwargs["concept_id"])


class MyEnrollmentsView(generics.ListAPIView):
    serializer_class = EnrollmentSerializer

    def get_queryset(self):
        return Enrollment.objects.filter(
            student=self.request.user, is_active=True
        ).select_related("course")


class CourseKnowledgeGraphView(APIView):
    """Knowledge graph payload for the lecturer Cytoscape.js visualisation.

    Returns nodes (concepts) + edges (prerequisites) + class-level mastery
    heatmap so a lecturer can see at a glance which concepts the class is
    struggling with. Optionally scoped to a specific class via
    ``?class_id=N`` so a lecturer who teaches several sections can compare.
    """

    permission_classes = (IsLecturerOrAdmin,)

    def get(self, request, course_id):
        from adaptive.models import MasteryState
        from accounts.models import User

        course = get_object_or_404(Course, pk=course_id)
        concepts = list(
            Concept.objects.filter(course=course, is_active=True)
            .order_by("order")
            .values("id", "code", "name", "description", "order")
        )
        concept_ids = [c["id"] for c in concepts]

        edges_raw = ConceptPrerequisite.objects.filter(
            concept_id__in=concept_ids,
            prerequisite_id__in=concept_ids,
        ).values("concept_id", "prerequisite_id")

        # Optional per-class scoping for the heatmap.
        class_id = request.query_params.get("class_id")
        students_qs = User.objects.filter(role=User.Role.STUDENT)
        if class_id:
            students_qs = students_qs.filter(
                class_memberships__student_class_id=class_id,
            )
        student_ids = list(students_qs.values_list("id", flat=True))

        mastery_per_concept = {}
        struggling_per_concept: dict[int, list[int]] = {}
        if student_ids and concept_ids:
            mastery_per_concept = dict(
                MasteryState.objects
                .filter(student_id__in=student_ids, concept_id__in=concept_ids)
                .values("concept_id")
                .annotate(avg=Avg("p_mastery"))
                .values_list("concept_id", "avg")
            )
            struggling_qs = (
                MasteryState.objects
                .filter(
                    student_id__in=student_ids,
                    concept_id__in=concept_ids,
                    p_mastery__lt=0.5,
                    attempt_count__gte=3,
                )
                .values_list("concept_id", "student_id")
            )
            for cid, sid in struggling_qs:
                struggling_per_concept.setdefault(cid, []).append(sid)

        nodes = []
        for c in concepts:
            avg = mastery_per_concept.get(c["id"])
            nodes.append({
                "data": {
                    "id": str(c["id"]),
                    "code": c["code"],
                    "label": c["name"],
                    "order": c["order"],
                    "avg_mastery": round(avg, 3) if avg is not None else None,
                    "mastery_band": _mastery_band(avg),
                    "struggling_count": len(struggling_per_concept.get(c["id"], [])),
                    "struggling_student_ids": struggling_per_concept.get(c["id"], []),
                },
            })
        edges = [
            {
                "data": {
                    "id": f"e-{e['prerequisite_id']}-{e['concept_id']}",
                    "source": str(e["prerequisite_id"]),
                    "target": str(e["concept_id"]),
                },
            }
            for e in edges_raw
        ]

        return Response({
            "course": {
                "id": course.id,
                "code": course.code,
                "name": course.name,
            },
            "students_in_scope": len(student_ids),
            "nodes": nodes,
            "edges": edges,
        })


def _mastery_band(avg):
    if avg is None:
        return "unknown"
    if avg < 0.4:
        return "low"
    if avg < 0.7:
        return "medium"
    return "high"
