"""
Read-only endpoints exposing the fairness audit log to admins.
"""
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminUser

from .models import FairnessAudit


class FairnessAuditListView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request):
        target = request.query_params.get("target")
        passed = request.query_params.get("passed")

        qs = FairnessAudit.objects.all().select_related("reviewed_by").order_by("-created_at")
        if target:
            qs = qs.filter(target_name=target)
        if passed in ("true", "false"):
            qs = qs.filter(passed=(passed == "true"))

        audits = []
        for a in qs[:100]:
            audits.append({
                "id": a.id,
                "target_name": a.target_name,
                "kind": a.kind,
                "passed": a.passed,
                "violations_count": len(a.violations or []),
                "violations": a.violations,
                "sensitive_attributes": a.sensitive_attributes,
                "sample_size": a.sample_size,
                "reviewed_by": a.reviewed_by.username if a.reviewed_by else None,
                "created_at": a.created_at,
            })

        return Response({"audits": audits, "count": len(audits)})


class FairnessAuditDetailView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request, pk):
        try:
            audit = FairnessAudit.objects.select_related("reviewed_by").get(pk=pk)
        except FairnessAudit.DoesNotExist:
            return Response({"detail": "Audit not found."}, status=404)
        return Response({
            "id": audit.id,
            "target_name": audit.target_name,
            "kind": audit.kind,
            "passed": audit.passed,
            "violations": audit.violations,
            "metrics": audit.metrics,
            "sensitive_attributes": audit.sensitive_attributes,
            "sample_size": audit.sample_size,
            "reviewed_by": audit.reviewed_by.username if audit.reviewed_by else None,
            "notes": audit.notes,
            "created_at": audit.created_at,
        })
