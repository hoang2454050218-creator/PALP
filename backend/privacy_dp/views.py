"""Admin-only DP endpoints — budgets + recent queries.

Public DP-protected analytics endpoints land in Phase 6B; these two
endpoints are the audit surface so an admin can answer
"how much ε did we spend this week?" in the dashboard.
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsLecturerOrAdmin

from privacy_dp.models import DPQueryLog, EpsilonBudget


class BudgetListView(APIView):
    permission_classes = [IsAuthenticated, IsLecturerOrAdmin]

    def get(self, request):
        rows = EpsilonBudget.objects.order_by("-period_start", "scope")[:50]
        return Response(
            {
                "budgets": [
                    {
                        "id": b.id,
                        "scope": b.scope,
                        "period_start": b.period_start.isoformat(),
                        "period_end": b.period_end.isoformat(),
                        "epsilon_total": b.epsilon_total,
                        "epsilon_spent": b.epsilon_spent,
                        "remaining": b.remaining,
                    }
                    for b in rows
                ]
            }
        )


class QueryLogView(APIView):
    permission_classes = [IsAuthenticated, IsLecturerOrAdmin]

    def get(self, request):
        rows = (
            DPQueryLog.objects
            .select_related("budget", "actor")
            .order_by("-created_at")[:100]
        )
        return Response(
            {
                "queries": [
                    {
                        "id": q.id,
                        "scope": q.budget.scope,
                        "actor_id": q.actor_id,
                        "mechanism": q.mechanism,
                        "query_kind": q.query_kind,
                        "epsilon_spent": q.epsilon_spent,
                        "sensitivity": q.sensitivity,
                        "raw_value": q.raw_value,
                        "noisy_value": q.noisy_value,
                        "sample_size": q.sample_size,
                        "created_at": q.created_at.isoformat(),
                    }
                    for q in rows
                ]
            }
        )
