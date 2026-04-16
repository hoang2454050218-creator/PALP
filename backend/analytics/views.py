from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.permissions import IsLecturerOrAdmin, IsClassMember, IsAdminUser
from .models import DataQualityLog, KPIDefinition, KPILineageLog, PilotReport
from .serializers import (
    DataQualityLogSerializer,
    KPIDefinitionSerializer,
    KPILineageSerializer,
    KPISnapshotSerializer,
    PilotReportSerializer,
)
from .services import generate_kpi_snapshot


class KPISnapshotView(APIView):
    permission_classes = (IsLecturerOrAdmin, IsClassMember)

    def get(self, request, class_id):
        week = int(request.query_params.get("week", 1))
        data = generate_kpi_snapshot(class_id, week)
        return Response(KPISnapshotSerializer(data).data)


class PilotReportListView(generics.ListAPIView):
    serializer_class = PilotReportSerializer
    permission_classes = (IsAdminUser,)
    queryset = PilotReport.objects.all()


class PilotReportDetailView(generics.RetrieveAPIView):
    serializer_class = PilotReportSerializer
    permission_classes = (IsAdminUser,)
    queryset = PilotReport.objects.all()


class DataQualityListView(generics.ListAPIView):
    serializer_class = DataQualityLogSerializer
    permission_classes = (IsAdminUser,)
    queryset = DataQualityLog.objects.all()


class KPIRegistryView(generics.ListAPIView):
    serializer_class = KPIDefinitionSerializer
    permission_classes = (IsLecturerOrAdmin,)
    queryset = KPIDefinition.objects.prefetch_related("versions", "lineage_logs")


class KPIRegistryDetailView(generics.RetrieveAPIView):
    serializer_class = KPIDefinitionSerializer
    permission_classes = (IsLecturerOrAdmin,)
    queryset = KPIDefinition.objects.prefetch_related("versions", "lineage_logs")
    lookup_field = "code"


class KPILineageListView(generics.ListAPIView):
    serializer_class = KPILineageSerializer
    permission_classes = (IsLecturerOrAdmin,)

    def get_queryset(self):
        qs = KPILineageLog.objects.select_related("kpi")
        kpi_code = self.request.query_params.get("kpi")
        if kpi_code:
            qs = qs.filter(kpi__code=kpi_code)
        class_id = self.request.query_params.get("class_id")
        if class_id:
            qs = qs.filter(class_id=class_id)
        return qs
