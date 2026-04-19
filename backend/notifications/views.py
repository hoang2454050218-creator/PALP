"""HTTP endpoints for the Notifications app.

| Method | Path                          | Auth                |
| ------ | ----------------------------- | ------------------- |
| GET    | ``/`` (list)                  | Authenticated       |
| GET    | ``unread-count/``             | Authenticated       |
| POST   | ``mark-read/``                | Authenticated       |
| POST   | ``<id>/read/``                | Authenticated       |
| GET    | ``preference/``               | Authenticated       |
| PATCH  | ``preference/``               | Authenticated       |
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import Notification, NotificationPreference
from notifications.serializers import (
    NotificationPreferenceSerializer,
    NotificationSerializer,
)
from notifications.services import ensure_pref, mark_read, unread_count


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        only_unread = request.query_params.get("unread") == "true"
        qs = Notification.objects.filter(user=request.user)
        if only_unread:
            qs = qs.filter(read_at__isnull=True)
        qs = qs[: int(request.query_params.get("limit", 50))]
        return Response(
            {"notifications": NotificationSerializer(qs, many=True).data}
        )


class UnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"unread": unread_count(user=request.user)})


class MarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ids = request.data.get("ids") or []
        if not isinstance(ids, list):
            return Response(
                {"detail": "ids must be a list."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        marked = mark_read(user=request.user, ids=ids)
        return Response({"marked": marked})


class MarkOneReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        marked = mark_read(user=request.user, ids=[notification_id])
        return Response({"marked": marked})


class PreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pref = ensure_pref(request.user)
        return Response(NotificationPreferenceSerializer(pref).data)

    def patch(self, request):
        pref = ensure_pref(request.user)
        serializer = NotificationPreferenceSerializer(
            pref, data=request.data, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
