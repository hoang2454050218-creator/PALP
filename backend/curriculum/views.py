from rest_framework import generics, viewsets
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsLecturerOrAdmin
from .models import Course, Enrollment, Concept, Milestone, MicroTask, SupplementaryContent
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
