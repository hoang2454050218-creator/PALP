from __future__ import annotations

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BenchmarkDataset, BenchmarkRun
from .permissions import IsAdminOrLecturer
from .serializers import BenchmarkDatasetSerializer, BenchmarkRunSerializer
from .services import (
    ensure_default_datasets,
    list_predictors,
    list_runs,
    run_benchmark,
)


class BenchmarkDatasetListView(generics.ListAPIView):
    serializer_class = BenchmarkDatasetSerializer
    permission_classes = [IsAuthenticated, IsAdminOrLecturer]

    def get_queryset(self):
        ensure_default_datasets()
        return BenchmarkDataset.objects.all()


class BenchmarkRunListView(generics.ListAPIView):
    serializer_class = BenchmarkRunSerializer
    permission_classes = [IsAuthenticated, IsAdminOrLecturer]

    def get_queryset(self):
        dataset_key = self.request.query_params.get("dataset")
        return list_runs(dataset_key)


class BenchmarkRunDetailView(generics.RetrieveAPIView):
    serializer_class = BenchmarkRunSerializer
    permission_classes = [IsAuthenticated, IsAdminOrLecturer]
    queryset = BenchmarkRun.objects.select_related("dataset").prefetch_related("results")
    lookup_field = "id"


class BenchmarkRunTriggerView(APIView):
    """POST /api/benchmarks/run — staff-only."""

    permission_classes = [IsAuthenticated, IsAdminOrLecturer]

    def post(self, request):
        dataset_key = request.data.get("dataset")
        predictor = request.data.get("predictor")
        seed = request.data.get("seed")
        sample_size = request.data.get("sample_size")
        notes = request.data.get("notes", "")

        if not dataset_key or not predictor:
            return Response(
                {"detail": "Both 'dataset' and 'predictor' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if predictor not in list_predictors():
            return Response(
                {
                    "detail": f"Unknown predictor '{predictor}'.",
                    "available": list_predictors(),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        ensure_default_datasets()
        try:
            dataset = BenchmarkDataset.objects.get(key=dataset_key)
        except BenchmarkDataset.DoesNotExist:
            return Response(
                {"detail": f"Dataset '{dataset_key}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        run = run_benchmark(
            dataset,
            predictor=predictor,
            seed=int(seed) if seed is not None else None,
            sample_size=int(sample_size) if sample_size is not None else None,
            notes=notes,
            requested_by=request.user,
        )
        return Response(
            BenchmarkRunSerializer(run).data,
            status=status.HTTP_201_CREATED,
        )


class BenchmarkPredictorListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrLecturer]

    def get(self, request):
        return Response({"predictors": list_predictors()})
