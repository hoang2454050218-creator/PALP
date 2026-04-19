"""HTTP endpoints for the Bandit app.

| Method | Path                                  | Auth                |
| ------ | ------------------------------------- | ------------------- |
| POST   | ``select/``                           | Authenticated       |
| POST   | ``decisions/<id>/reward/``            | Authenticated owner |
| GET    | ``experiments/<key>/stats/``          | IsLecturerOrAdmin   |

The endpoints are intentionally generic so the future nudge dispatcher
can call ``select/`` from server code (with admin token) AND a
research dashboard can use ``stats/`` to compare arms.
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsLecturerOrAdmin

from bandit.models import (
    BanditArm,
    BanditDecision,
    BanditExperiment,
    BanditPosterior,
)
from bandit.services import (
    BanditExperimentInactive,
    NoEnabledArms,
    record_reward,
    select_arm,
)


class BanditSelectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        experiment_key = request.data.get("experiment_key")
        context_key = request.data.get("context_key", "default")
        if not experiment_key:
            return Response(
                {"detail": "experiment_key is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = select_arm(
                experiment_key=experiment_key,
                user=request.user,
                context_key=context_key,
            )
        except BanditExperiment.DoesNotExist:
            return Response(
                {"detail": "Experiment không tồn tại."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except BanditExperimentInactive:
            return Response(
                {"detail": "Experiment đang tạm dừng."},
                status=status.HTTP_409_CONFLICT,
            )
        except NoEnabledArms:
            return Response(
                {"detail": "Experiment không có arm nào enabled."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(
            {
                "decision_id": result.decision.id,
                "arm": {
                    "key": result.arm.key,
                    "title": result.arm.title,
                    "payload": result.arm.payload,
                },
                "sampled_value": result.sampled_value,
                "samples": result.samples,
            },
            status=status.HTTP_201_CREATED,
        )


class BanditRewardView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, decision_id):
        try:
            decision = BanditDecision.objects.select_related("arm").get(pk=decision_id)
        except BanditDecision.DoesNotExist:
            return Response(
                {"detail": "Decision không tồn tại."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if decision.user_id != request.user.id and not getattr(
            request.user, "is_admin_user", False,
        ):
            return Response(
                {"detail": "Bạn không sở hữu decision này."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            value = float(request.data.get("value"))
        except (TypeError, ValueError):
            return Response(
                {"detail": "value (0..1) is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reward = record_reward(
            decision=decision,
            value=value,
            notes=request.data.get("notes", ""),
        )
        return Response(
            {
                "decision_id": decision.id,
                "reward_value": reward.value,
                "notes": reward.notes,
            }
        )


class BanditStatsView(APIView):
    permission_classes = [IsAuthenticated, IsLecturerOrAdmin]

    def get(self, request, experiment_key):
        experiment = BanditExperiment.objects.filter(key=experiment_key).first()
        if not experiment:
            return Response(
                {"detail": "Experiment không tồn tại."},
                status=status.HTTP_404_NOT_FOUND,
            )
        arms = list(experiment.arms.all())
        posteriors = list(
            BanditPosterior.objects
            .filter(arm__experiment=experiment)
            .select_related("arm")
        )
        per_arm = {a.id: {"key": a.key, "title": a.title, "posteriors": []} for a in arms}
        for p in posteriors:
            per_arm[p.arm_id]["posteriors"].append(
                {
                    "context_key": p.context_key,
                    "alpha": p.alpha,
                    "beta": p.beta,
                    "expected_reward": p.expected_reward,
                    "pulls": p.pulls,
                    "rewards_sum": p.rewards_sum,
                }
            )
        return Response({"experiment_key": experiment.key, "arms": list(per_arm.values())})
