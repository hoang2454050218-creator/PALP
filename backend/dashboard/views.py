from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import LecturerClassAssignment, User
from accounts.permissions import IsLecturerOrAdmin
from events.services import audit_log
from palp.idempotency import idempotent
from events.models import EventLog
from .models import Alert, InterventionAction
from .serializers import (
    AlertSerializer, DismissAlertSerializer,
    InterventionActionSerializer, CreateInterventionSerializer,
    ClassOverviewSerializer,
)
from .services import get_class_overview


def _verify_class_access(user, class_id):
    if user.is_admin_user:
        return
    has_access = LecturerClassAssignment.objects.filter(
        lecturer=user, student_class_id=class_id,
    ).exists()
    if not has_access:
        raise PermissionDenied("Bạn không có quyền truy cập lớp này.")


class ClassOverviewView(APIView):
    permission_classes = (IsLecturerOrAdmin,)

    def get(self, request, class_id):
        _verify_class_access(request.user, class_id)
        overview = get_class_overview(class_id)
        serializer = ClassOverviewSerializer(overview)
        return Response(serializer.data)


class AlertListView(generics.ListAPIView):
    serializer_class = AlertSerializer
    permission_classes = (IsLecturerOrAdmin,)

    def get_queryset(self):
        qs = Alert.objects.select_related("student", "concept", "milestone")

        if not self.request.user.is_admin_user:
            allowed_class_ids = LecturerClassAssignment.objects.filter(
                lecturer=self.request.user,
            ).values_list("student_class_id", flat=True)
            qs = qs.filter(student_class_id__in=allowed_class_ids)

        class_id = self.request.query_params.get("class_id")
        if class_id:
            _verify_class_access(self.request.user, class_id)
            qs = qs.filter(student_class_id=class_id)

        severity = self.request.query_params.get("severity")
        if severity:
            qs = qs.filter(severity=severity)

        alert_status = self.request.query_params.get("status", "active")
        if alert_status:
            qs = qs.filter(status=alert_status)

        now = timezone.now()
        qs = qs.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now) |
            ~Q(status=Alert.AlertStatus.ACTIVE)
        )

        return qs


class DismissAlertView(APIView):
    permission_classes = (IsLecturerOrAdmin,)

    @idempotent(required=False)
    def post(self, request, pk):
        alert = Alert.objects.select_related("student_class").get(id=pk)
        if alert.student_class_id:
            _verify_class_access(request.user, alert.student_class_id)

        serializer = DismissAlertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        alert.status = Alert.AlertStatus.DISMISSED
        alert.dismissed_by = request.user
        alert.dismiss_reason_code = serializer.validated_data["dismiss_reason_code"]
        alert.dismiss_note = serializer.validated_data.get("dismiss_note", "")
        alert.resolved_at = timezone.now()
        alert.save()

        audit_log(
            request.user,
            EventLog.EventName.ALERT_DISMISSED,
            {
                "alert_id": alert.id,
                "student_id": alert.student_id,
                "trigger_type": alert.trigger_type,
                "dismiss_reason_code": alert.dismiss_reason_code,
            },
        )

        return Response(AlertSerializer(alert).data)


class CreateInterventionView(APIView):
    permission_classes = (IsLecturerOrAdmin,)

    @idempotent(required=True)
    def post(self, request):
        serializer = CreateInterventionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        alert = Alert.objects.get(id=data["alert_id"])
        if alert.student_class_id:
            _verify_class_access(request.user, alert.student_class_id)

        action = InterventionAction.objects.create(
            alert=alert,
            lecturer=request.user,
            action_type=data["action_type"],
            message=data.get("message", ""),
        )
        targets = User.objects.filter(id__in=data["target_student_ids"])
        action.targets.set(targets)

        alert.status = Alert.AlertStatus.RESOLVED
        alert.resolved_at = timezone.now()
        alert.save()

        audit_log(
            request.user,
            EventLog.EventName.INTERVENTION_CREATED,
            {
                "intervention_id": action.id,
                "alert_id": alert.id,
                "action_type": data["action_type"],
                "target_student_ids": data["target_student_ids"],
            },
        )

        return Response(
            InterventionActionSerializer(action).data,
            status=status.HTTP_201_CREATED,
        )


class InterventionHistoryView(generics.ListAPIView):
    serializer_class = InterventionActionSerializer
    permission_classes = (IsLecturerOrAdmin,)

    def get_queryset(self):
        qs = InterventionAction.objects.select_related("alert", "lecturer")

        if not self.request.user.is_admin_user:
            allowed_class_ids = LecturerClassAssignment.objects.filter(
                lecturer=self.request.user,
            ).values_list("student_class_id", flat=True)
            qs = qs.filter(alert__student_class_id__in=allowed_class_ids)

        class_id = self.request.query_params.get("class_id")
        if class_id:
            _verify_class_access(self.request.user, class_id)
            qs = qs.filter(alert__student_class_id=class_id)
        return qs


class UpdateFollowUpView(APIView):
    permission_classes = (IsLecturerOrAdmin,)

    def patch(self, request, pk):
        action = InterventionAction.objects.select_related("alert").get(id=pk)
        if action.alert.student_class_id:
            _verify_class_access(request.user, action.alert.student_class_id)

        new_status = request.data.get("follow_up_status")
        if new_status and new_status in dict(InterventionAction.FollowUpStatus.choices):
            action.follow_up_status = new_status
            action.save(update_fields=["follow_up_status", "updated_at"])
        return Response(InterventionActionSerializer(action).data)
