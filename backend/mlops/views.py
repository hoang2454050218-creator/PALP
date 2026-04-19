"""
Admin-only read endpoints for the MLOps registry.

Mutations are intentionally driven by management commands / Celery tasks
to keep the model lifecycle deterministic and auditable. The HTTP layer
only exposes inspection so dashboards and the Cursor-based control plane
can read without needing direct DB access.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminUser

from .models import DriftReport, ModelRegistry, ModelVersion, ShadowComparison


class ModelRegistryListView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request):
        items = []
        for reg in ModelRegistry.objects.all().select_related("owner"):
            prod = reg.production_version
            items.append({
                "name": reg.name,
                "model_type": reg.model_type,
                "owner": reg.owner.username if reg.owner else None,
                "production_semver": prod.semver if prod else None,
                "production_metrics": prod.metrics_json if prod else None,
                "fairness_passed": prod.fairness_passed if prod else None,
                "epsilon_dp": prod.epsilon_dp if prod else None,
                "n_versions": reg.versions.count(),
                "updated_at": reg.updated_at,
            })
        return Response({"models": items, "count": len(items)})


class ModelVersionListView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request, name):
        try:
            registry = ModelRegistry.objects.get(name=name)
        except ModelRegistry.DoesNotExist:
            return Response(
                {"detail": "Registry not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        versions = []
        for v in registry.versions.all():
            versions.append({
                "semver": v.semver,
                "status": v.status,
                "metrics": v.metrics_json,
                "fairness_passed": v.fairness_passed,
                "epsilon_dp": v.epsilon_dp,
                "model_card_path": v.model_card_path,
                "promoted_at": v.promoted_at,
                "created_at": v.created_at,
            })
        return Response({
            "name": registry.name,
            "model_type": registry.model_type,
            "versions": versions,
        })


class DriftReportListView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request, name):
        try:
            registry = ModelRegistry.objects.get(name=name)
        except ModelRegistry.DoesNotExist:
            return Response(
                {"detail": "Registry not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        reports = (
            DriftReport.objects
            .filter(model_version__registry=registry)
            .select_related("model_version")
            .order_by("-created_at")[:50]
        )
        return Response({
            "name": registry.name,
            "reports": [
                {
                    "semver": r.model_version.semver,
                    "severity": r.severity,
                    "drift_detected": r.drift_detected,
                    "sample_size": r.sample_size,
                    "window_start": r.window_start,
                    "window_end": r.window_end,
                    "feature_summary": r.feature_summary,
                }
                for r in reports
            ],
        })


class ShadowComparisonListView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request, name):
        try:
            registry = ModelRegistry.objects.get(name=name)
        except ModelRegistry.DoesNotExist:
            return Response(
                {"detail": "Registry not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        rows = (
            ShadowComparison.objects
            .filter(candidate_version__registry=registry)
            .select_related("candidate_version", "baseline_version")
            .order_by("-created_at")[:50]
        )
        return Response({
            "name": registry.name,
            "comparisons": [
                {
                    "candidate_semver": r.candidate_version.semver,
                    "baseline_semver": r.baseline_version.semver,
                    "n_predictions": r.n_predictions,
                    "mean_abs_diff": r.mean_abs_diff,
                    "p95_abs_diff": r.p95_abs_diff,
                    "agreement_pct": r.agreement_pct,
                    "window_start": r.window_start,
                    "window_end": r.window_end,
                }
                for r in rows
            ],
        })
