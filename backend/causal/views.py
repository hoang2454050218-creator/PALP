"""
Read-only endpoints exposing causal experiment state to admins.

Mutations stay in management commands / Celery tasks (so pre-registration
discipline isn't accidentally undermined by a click on the dashboard).
"""
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminUser

from .models import CausalEvaluation, CausalExperiment


class CausalExperimentListView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request):
        items = []
        for ce in CausalExperiment.objects.select_related("experiment", "locked_by"):
            items.append({
                "experiment": ce.experiment.name,
                "experiment_status": ce.experiment.status,
                "primary_outcome_metric": ce.primary_outcome_metric,
                "outcome_kind": ce.outcome_kind,
                "randomization_unit": ce.randomization_unit,
                "is_locked": ce.is_locked,
                "locked_at": ce.locked_at,
                "irb_reference": ce.irb_reference,
                "n_evaluations": ce.evaluations.count(),
            })
        return Response({"experiments": items, "count": len(items)})


class CausalExperimentDetailView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request, name):
        try:
            ce = CausalExperiment.objects.select_related("experiment").get(experiment__name=name)
        except CausalExperiment.DoesNotExist:
            return Response({"detail": "Causal experiment not found."}, status=404)

        evaluations = []
        for ev in ce.evaluations.all():
            evaluations.append({
                "estimator": ev.estimator,
                "ate": ev.ate,
                "ate_ci_low": ev.ate_ci_low,
                "ate_ci_high": ev.ate_ci_high,
                "p_value": ev.p_value,
                "n_treatment": ev.n_treatment,
                "n_control": ev.n_control,
                "fairness_audit_id": ev.fairness_audit_id,
                "created_at": ev.created_at,
            })

        return Response({
            "experiment": ce.experiment.name,
            "pre_registration": ce.pre_registration,
            "primary_outcome_metric": ce.primary_outcome_metric,
            "secondary_outcomes": ce.secondary_outcomes,
            "outcome_kind": ce.outcome_kind,
            "randomization_unit": ce.randomization_unit,
            "cuped_covariate": ce.cuped_covariate,
            "expected_effect_size": ce.expected_effect_size,
            "target_sample_per_arm": ce.target_sample_per_arm,
            "irb_reference": ce.irb_reference,
            "is_locked": ce.is_locked,
            "locked_at": ce.locked_at,
            "amendments_log": ce.amendments_log,
            "evaluations": evaluations,
        })
