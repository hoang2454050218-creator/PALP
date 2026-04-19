from __future__ import annotations

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Datasheet, ModelCard, ReproducibilityKit
from .permissions import IsAdminOrLecturer, IsPublicOrAdmin, _is_admin
from .serializers import (
    DatasheetSerializer,
    ModelCardSerializer,
    ReproducibilityKitSerializer,
)
from .services import (
    bundle_repro_kit,
    draft_datasheet,
    draft_model_card,
    promote_model_card,
)


class ModelCardListView(generics.ListAPIView):
    serializer_class = ModelCardSerializer
    permission_classes = [IsAuthenticated, IsPublicOrAdmin]

    def get_queryset(self):
        user = self.request.user
        qs = ModelCard.objects.order_by("-updated_at")
        if _is_admin(user):
            return qs
        return qs.filter(status=ModelCard.Status.PUBLISHED)


class ModelCardDetailView(generics.RetrieveAPIView):
    serializer_class = ModelCardSerializer
    permission_classes = [IsAuthenticated, IsPublicOrAdmin]
    queryset = ModelCard.objects.all()
    lookup_field = "id"


class ModelCardDraftView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrLecturer]

    def post(self, request):
        model_label = request.data.get("model_label")
        if not model_label:
            return Response(
                {"detail": "model_label required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        registry_entry = None
        registry_name = request.data.get("registry_name")
        if registry_name:
            try:
                from mlops.models import ModelRegistry
                registry_entry = ModelRegistry.objects.filter(name=registry_name).first()
            except Exception:
                registry_entry = None

        benchmark_run = None
        run_id = request.data.get("benchmark_run_id")
        if run_id:
            try:
                from benchmarks.models import BenchmarkRun
                benchmark_run = BenchmarkRun.objects.filter(id=run_id).first()
            except Exception:
                benchmark_run = None

        card = draft_model_card(
            model_label=model_label,
            title=request.data.get("title"),
            requested_by=request.user,
            registry_entry=registry_entry,
            benchmark_run=benchmark_run,
        )
        return Response(
            ModelCardSerializer(card).data,
            status=status.HTTP_201_CREATED,
        )


class ModelCardPromoteView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrLecturer]

    def post(self, request, id: int):
        try:
            card = ModelCard.objects.get(id=id)
        except ModelCard.DoesNotExist:
            return Response(
                {"detail": "Model card not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        target = request.data.get("target", "published")
        try:
            card = promote_model_card(card, target=target)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ModelCardSerializer(card).data)


class DatasheetListView(generics.ListAPIView):
    serializer_class = DatasheetSerializer
    permission_classes = [IsAuthenticated, IsPublicOrAdmin]

    def get_queryset(self):
        user = self.request.user
        qs = Datasheet.objects.order_by("-updated_at")
        if _is_admin(user):
            return qs
        return qs.filter(status=Datasheet.Status.PUBLISHED)


class DatasheetDraftView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrLecturer]

    def post(self, request):
        dataset_key = request.data.get("dataset_key")
        if not dataset_key:
            return Response(
                {"detail": "dataset_key required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        sheet = draft_datasheet(
            dataset_key=dataset_key,
            title=request.data.get("title"),
            motivation=request.data.get("motivation", ""),
            composition=request.data.get("composition") or {},
            requested_by=request.user,
        )
        return Response(
            DatasheetSerializer(sheet).data,
            status=status.HTTP_201_CREATED,
        )


class ReproKitListView(generics.ListAPIView):
    serializer_class = ReproducibilityKitSerializer
    permission_classes = [IsAuthenticated, IsAdminOrLecturer]
    queryset = ReproducibilityKit.objects.all()


class ReproKitCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrLecturer]

    def post(self, request):
        card_id = request.data.get("model_card_id")
        sheet_id = request.data.get("datasheet_id")
        if not card_id or not sheet_id:
            return Response(
                {"detail": "model_card_id and datasheet_id required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            card = ModelCard.objects.get(id=card_id)
            sheet = Datasheet.objects.get(id=sheet_id)
        except (ModelCard.DoesNotExist, Datasheet.DoesNotExist):
            return Response(
                {"detail": "Model card or datasheet not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        kit = bundle_repro_kit(
            model_card=card,
            datasheet=sheet,
            benchmark_run_id=request.data.get("benchmark_run_id"),
            commit_hash=request.data.get("commit_hash", ""),
            seed=int(request.data.get("seed", 42)),
            title=request.data.get("title"),
            requested_by=request.user,
        )
        return Response(
            ReproducibilityKitSerializer(kit).data,
            status=status.HTTP_201_CREATED,
        )
