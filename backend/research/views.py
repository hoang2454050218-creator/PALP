from __future__ import annotations

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AnonymizedExport, ResearchParticipation, ResearchProtocol
from .permissions import IsAdminOrPI, IsStudent, _is_admin
from .serializers import (
    AnonymizedExportSerializer,
    ResearchParticipationSerializer,
    ResearchProtocolSerializer,
)
from .services import decline, opt_in, withdraw


class ResearchProtocolListView(generics.ListCreateAPIView):
    """Admin list / create. Students see ACTIVE protocols only."""

    serializer_class = ResearchProtocolSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsAdminOrPI()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = ResearchProtocol.objects.order_by("-updated_at")
        if _is_admin(user) or getattr(user, "is_lecturer", False):
            return qs
        return qs.filter(status=ResearchProtocol.Status.ACTIVE)


class ResearchProtocolDetailView(generics.RetrieveUpdateAPIView):
    queryset = ResearchProtocol.objects.all()
    serializer_class = ResearchProtocolSerializer
    lookup_field = "code"

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH"):
            return [IsAuthenticated(), IsAdminOrPI()]
        return [IsAuthenticated()]


class MyResearchParticipationListView(generics.ListAPIView):
    serializer_class = ResearchParticipationSerializer
    permission_classes = [IsAuthenticated, IsStudent]

    def get_queryset(self):
        return (
            ResearchParticipation.objects
            .filter(student=self.request.user)
            .select_related("protocol")
            .order_by("-decided_at")
        )


class ResearchOptInView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def post(self, request, code: str):
        try:
            protocol = ResearchProtocol.objects.get(code=code)
        except ResearchProtocol.DoesNotExist:
            return Response(
                {"detail": "Đề cương nghiên cứu không tồn tại."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if protocol.status not in (
            ResearchProtocol.Status.APPROVED,
            ResearchProtocol.Status.ACTIVE,
        ):
            return Response(
                {"detail": "Đề cương chưa sẵn sàng nhận đăng ký."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        part = opt_in(request.user, protocol)
        return Response(
            ResearchParticipationSerializer(part).data,
            status=status.HTTP_201_CREATED,
        )


class ResearchWithdrawView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def post(self, request, code: str):
        try:
            protocol = ResearchProtocol.objects.get(code=code)
        except ResearchProtocol.DoesNotExist:
            return Response(
                {"detail": "Đề cương nghiên cứu không tồn tại."},
                status=status.HTTP_404_NOT_FOUND,
            )
        part = withdraw(request.user, protocol)
        if part is None:
            return Response(
                {"detail": "Bạn chưa từng đăng ký đề cương này."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ResearchParticipationSerializer(part).data)


class ResearchDeclineView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def post(self, request, code: str):
        try:
            protocol = ResearchProtocol.objects.get(code=code)
        except ResearchProtocol.DoesNotExist:
            return Response(
                {"detail": "Đề cương nghiên cứu không tồn tại."},
                status=status.HTTP_404_NOT_FOUND,
            )
        part = decline(request.user, protocol)
        return Response(ResearchParticipationSerializer(part).data)


class AnonymizedExportListView(generics.ListAPIView):
    serializer_class = AnonymizedExportSerializer
    permission_classes = [IsAuthenticated, IsAdminOrPI]

    def get_queryset(self):
        protocol_code = self.request.query_params.get("protocol")
        qs = AnonymizedExport.objects.select_related("protocol").order_by("-created_at")
        if protocol_code:
            qs = qs.filter(protocol__code=protocol_code)
        return qs[:200]
