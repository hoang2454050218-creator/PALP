from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminUser, IsStudent
from palp.idempotency import idempotent

from .constants import CONSENT_VERSION, EXPORT_GLOSSARY
from .models import AuditLog, ConsentRecord, DataDeletionRequest, PrivacyIncident
from .serializers import (
    AuditLogSerializer,
    ConsentRecordSerializer,
    ConsentStatusSerializer,
    DataDeleteRequestSerializer,
    DeletionRequestStatusSerializer,
    GrantConsentSerializer,
    PrivacyIncidentCreateSerializer,
    PrivacyIncidentSerializer,
)
from .services import (
    delete_user_data,
    export_user_data,
    get_client_ip,
    get_consent_status,
    log_audit,
    sync_user_consent_flag,
)


class ConsentStatusView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        statuses = get_consent_status(request.user)
        serializer = ConsentStatusSerializer(statuses, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = GrantConsentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip = get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]
        version = serializer.validated_data.get("version", CONSENT_VERSION)
        records = []

        for item in serializer.validated_data["consents"]:
            record = ConsentRecord.objects.create(
                user=request.user,
                purpose=item["purpose"],
                granted=item["granted"],
                version=version,
                ip_address=ip,
                user_agent=user_agent,
            )
            records.append(record)

        sync_user_consent_flag(request.user)

        log_audit(
            actor=request.user,
            action=AuditLog.Action.CONSENT_CHANGE,
            resource="privacy.consent",
            detail={
                "consents": [
                    {"purpose": r.purpose, "granted": r.granted}
                    for r in records
                ],
                "version": version,
            },
            ip_address=ip,
            request_id=getattr(request, "request_id", None),
        )

        statuses = get_consent_status(request.user)
        return Response(
            ConsentStatusSerializer(statuses, many=True).data,
            status=status.HTTP_200_OK,
        )


class ConsentHistoryView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        records = ConsentRecord.objects.filter(user=request.user)[:100]
        return Response(ConsentRecordSerializer(records, many=True).data)


class DataExportView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        target_user = request.user

        if request.user.is_admin_user:
            target_id = request.query_params.get("user_id")
            if target_id:
                from accounts.models import User
                try:
                    target_user = User.objects.get(id=target_id)
                except User.DoesNotExist:
                    return Response(
                        {"detail": "User not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )

        if not request.user.is_admin_user and target_user != request.user:
            return Response(
                {"detail": "Bạn chỉ có thể xuất dữ liệu của chính mình."},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = export_user_data(target_user)

        ip = get_client_ip(request)
        log_audit(
            actor=request.user,
            action=AuditLog.Action.EXPORT,
            resource="privacy.export",
            target_user=target_user,
            detail={"tiers": list(data.keys())},
            ip_address=ip,
            request_id=getattr(request, "request_id", None),
        )

        return Response({
            "meta": {
                "exported_at": timezone.now().isoformat(),
                "user_id": target_user.id,
                "username": target_user.username,
                "format_version": "1.0",
                "glossary": EXPORT_GLOSSARY,
            },
            "data": data,
        })


class DataDeleteView(APIView):
    permission_classes = (IsAuthenticated,)

    @idempotent(required=True)
    def post(self, request):
        serializer = DataDeleteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_user = request.user
        tiers = serializer.validated_data["tiers"]

        if not request.user.is_admin_user and target_user != request.user:
            return Response(
                {"detail": "Bạn chỉ có thể xóa dữ liệu của chính mình."},
                status=status.HTTP_403_FORBIDDEN,
            )

        ip = get_client_ip(request)

        deletion_req = DataDeletionRequest.objects.create(
            user=target_user,
            tiers=tiers,
            status=DataDeletionRequest.RequestStatus.PROCESSING,
        )

        try:
            summary = delete_user_data(
                user=target_user,
                tiers=tiers,
                actor=request.user,
                ip_address=ip,
            )
            deletion_req.status = DataDeletionRequest.RequestStatus.COMPLETED
            deletion_req.result_summary = summary
            deletion_req.completed_at = timezone.now()
            deletion_req.save()
        except Exception:
            deletion_req.status = DataDeletionRequest.RequestStatus.FAILED
            deletion_req.save()
            raise

        return Response({
            "detail": "Dữ liệu đã được xử lý thành công.",
            "request": DeletionRequestStatusSerializer(deletion_req).data,
            "summary": summary,
        })


class DeletionRequestListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        qs = DataDeletionRequest.objects.filter(user=request.user)[:50]
        return Response(DeletionRequestStatusSerializer(qs, many=True).data)


class AuditLogView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        if request.user.is_admin_user:
            target_id = request.query_params.get("user_id")
            if target_id:
                qs = AuditLog.objects.filter(target_user_id=target_id)
            else:
                qs = AuditLog.objects.all()
        else:
            qs = AuditLog.objects.filter(target_user=request.user)

        qs = qs.select_related("actor", "target_user")[:100]
        return Response(AuditLogSerializer(qs, many=True).data)


class PrivacyIncidentView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request):
        qs = PrivacyIncident.objects.all()[:50]
        return Response(PrivacyIncidentSerializer(qs, many=True).data)

    def post(self, request):
        serializer = PrivacyIncidentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from datetime import timedelta
        incident = PrivacyIncident.objects.create(
            reported_by=request.user,
            severity=data["severity"],
            title=data["title"],
            description=data["description"],
            affected_user_count=data.get("affected_user_count", 0),
            affected_data_tiers=data.get("affected_data_tiers", []),
            sla_deadline=timezone.now() + timedelta(hours=48),
        )

        ip = get_client_ip(request)
        log_audit(
            actor=request.user,
            action=AuditLog.Action.INCIDENT,
            resource="privacy.incident",
            detail={
                "incident_id": incident.id,
                "severity": incident.severity,
                "title": incident.title,
            },
            ip_address=ip,
            request_id=getattr(request, "request_id", None),
        )

        return Response(
            PrivacyIncidentSerializer(incident).data,
            status=status.HTTP_201_CREATED,
        )
