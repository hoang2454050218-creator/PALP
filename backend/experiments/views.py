from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminUser

from .models import Experiment
from .services import assignment_map_for, compute_results


class MyAssignmentsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response({"assignments": assignment_map_for(request.user)})


class ExperimentResultsView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request, name):
        try:
            experiment = Experiment.objects.get(name=name)
        except Experiment.DoesNotExist:
            return Response(
                {"detail": "Experiment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({
            "experiment": experiment.name,
            "metric": experiment.primary_metric,
            "metric_kind": experiment.metric_kind,
            "results": compute_results(experiment),
        })
