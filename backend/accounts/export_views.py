import csv
import io

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.audit import log_audit
from accounts.models import User, ClassMembership, LecturerClassAssignment
from accounts.permissions import IsLecturerOrAdmin, IsClassMember
from palp.throttles import ExportThrottle


class ExportMyDataView(APIView):
    """GDPR Article 20: Data portability - user exports their own data."""

    permission_classes = (IsAuthenticated,)
    throttle_classes = (ExportThrottle,)

    def get(self, request):
        user = request.user
        log_audit(
            action="export_data",
            request=request,
            target_model="User",
            target_id=user.id,
            metadata={"scope": "self"},
        )

        data = {
            "profile": {
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "student_id": user.student_id,
                "phone": user.phone,
                "role": user.role,
                "consent_given": user.consent_given,
                "consent_given_at": str(user.consent_given_at) if user.consent_given_at else None,
                "created_at": str(user.created_at),
            },
            "enrollments": list(
                user.enrollments.values("course__name", "semester", "is_active")
            ) if hasattr(user, "enrollments") else [],
            "assessment_sessions": list(
                user.assessment_sessions.values(
                    "assessment__title", "score", "total_score", "status", "started_at", "completed_at"
                )
            ) if hasattr(user, "assessment_sessions") else [],
            "task_attempts": list(
                user.task_attempts.values(
                    "task__title", "score", "max_score", "is_correct", "created_at"
                )
            ) if hasattr(user, "task_attempts") else [],
            "event_logs": list(
                user.event_logs.values(
                    "event_name", "properties", "created_at"
                )[:500]
            ),
        }
        return Response(data)


class ExportClassDataView(APIView):
    """Lecturer exports aggregated class data as CSV."""

    permission_classes = (IsLecturerOrAdmin, IsClassMember)
    throttle_classes = (ExportThrottle,)

    def get(self, request, class_id):
        log_audit(
            action="export_data",
            request=request,
            target_model="StudentClass",
            target_id=class_id,
            metadata={"scope": "class"},
        )

        memberships = ClassMembership.objects.filter(
            student_class_id=class_id,
        ).select_related("student")

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["username", "full_name", "student_id", "joined_at"])
        for m in memberships:
            writer.writerow([
                m.student.username,
                m.student.get_full_name(),
                m.student.student_id,
                m.joined_at.isoformat(),
            ])

        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="class_{class_id}_export.csv"'
        return response


class DeleteMyDataView(APIView):
    """GDPR Article 17: Right to erasure - soft-delete user data."""

    permission_classes = (IsAuthenticated,)

    def delete(self, request):
        user = request.user
        log_audit(
            action="delete_data",
            request=request,
            target_model="User",
            target_id=user.id,
            metadata={"scope": "self_erasure"},
        )

        user.is_deleted = True
        user.deleted_at = timezone.now()
        user.is_active = False
        user.email = f"deleted_{user.id}@deleted.local"
        user.first_name = ""
        user.last_name = ""
        user.phone = ""
        user.student_id = ""
        user.avatar_url = ""
        user.save()

        return Response(
            {"detail": "Dữ liệu của bạn đã được xóa. Tài khoản đã bị vô hiệu hóa."},
            status=status.HTTP_200_OK,
        )
