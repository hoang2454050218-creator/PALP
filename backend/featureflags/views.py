from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import active_flags_for


class ActiveFlagsView(APIView):
    """Flags map served to the authenticated user."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response({"flags": active_flags_for(request.user)})
