"""HTTP endpoints for the agentic memory.

| Method | Path                  | Auth                          |
| ------ | --------------------- | ----------------------------- |
| GET    | ``me/``               | IsStudent (own, consent gate) |
| DELETE | ``me/``               | IsStudent (own)               |

Read-only "what coach remembers" panel is the first surface; the
DELETE endpoint is the user-facing "right to be forgotten" lever (the
playbook's privacy gate). Both endpoints return only the bounded
recall snapshot, not raw rows, to keep parity with the prompt-side
view of memory.
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsStudent

from coach_memory.models import (
    EpisodicMemory,
    ProceduralMemory,
    SemanticMemory,
)
from coach_memory.permissions import HasAgenticMemoryConsent
from coach_memory.services import recall


class MyMemoryView(APIView):
    permission_classes = [IsAuthenticated, IsStudent, HasAgenticMemoryConsent]

    def get(self, request):
        snapshot = recall(student=request.user)
        return Response(
            {
                "semantic": snapshot.semantic,
                "episodic": snapshot.episodic,
                "procedural": snapshot.procedural,
                "as_of": _now(),
            }
        )

    def delete(self, request):
        EpisodicMemory.objects.filter(student=request.user).delete()
        SemanticMemory.objects.filter(student=request.user).delete()
        ProceduralMemory.objects.filter(student=request.user).delete()
        return Response(
            {"status": "memory_cleared"}, status=status.HTTP_200_OK,
        )


def _now() -> str:
    from django.utils import timezone
    return timezone.now().isoformat()
