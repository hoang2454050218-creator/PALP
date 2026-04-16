from django.conf import settings
from django.db import models


class ConsentRecord(models.Model):
    class Purpose(models.TextChoices):
        ACADEMIC = "academic", "Dữ liệu học vụ lịch sử"
        BEHAVIORAL = "behavioral", "Dữ liệu hành vi học tập"
        INFERENCE = "inference", "Dữ liệu suy luận (mastery, risk)"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="consent_records",
    )
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    granted = models.BooleanField()
    version = models.CharField(max_length=20, default="1.0")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_consent_record"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "purpose", "-created_at"]),
        ]

    def __str__(self):
        action = "granted" if self.granted else "revoked"
        return f"{self.user.username} {action} [{self.purpose}] v{self.version}"


class AuditLog(models.Model):
    class Action(models.TextChoices):
        VIEW = "view", "Xem dữ liệu"
        EXPORT = "export", "Xuất dữ liệu"
        DELETE = "delete", "Xóa dữ liệu"
        ANONYMIZE = "anonymize", "Ẩn danh hóa"
        CONSENT_CHANGE = "consent_change", "Thay đổi đồng thuận"
        INCIDENT = "incident", "Sự cố bảo mật"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_actions",
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_targets",
    )
    resource = models.CharField(max_length=200)
    detail = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    request_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_audit_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["actor", "-created_at"]),
            models.Index(fields=["target_user", "-created_at"]),
            models.Index(fields=["action", "-created_at"]),
        ]

    def __str__(self):
        actor_name = self.actor.username if self.actor else "system"
        target_name = self.target_user.username if self.target_user else "n/a"
        return f"{actor_name} -> {self.action} [{self.resource}] target={target_name}"


class PrivacyIncident(models.Model):
    class Severity(models.TextChoices):
        LOW = "low", "Thấp"
        MEDIUM = "medium", "Trung bình"
        HIGH = "high", "Cao"
        CRITICAL = "critical", "Nghiêm trọng"

    class Status(models.TextChoices):
        OPEN = "open", "Đang mở"
        INVESTIGATING = "investigating", "Đang điều tra"
        RESOLVED = "resolved", "Đã xử lý"
        CLOSED = "closed", "Đóng"

    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="reported_incidents",
    )
    severity = models.CharField(max_length=10, choices=Severity.choices)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.OPEN)
    title = models.CharField(max_length=300)
    description = models.TextField()
    affected_user_count = models.PositiveIntegerField(default=0)
    affected_data_tiers = models.JSONField(default=list)
    resolution = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    sla_deadline = models.DateTimeField(
        help_text="48h from creation for response",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_privacy_incident"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.severity}] {self.title} ({self.status})"

    @property
    def is_within_sla(self):
        from django.utils import timezone
        if self.status in (self.Status.RESOLVED, self.Status.CLOSED):
            return True
        return timezone.now() <= self.sla_deadline


class DataDeletionRequest(models.Model):
    class RequestStatus(models.TextChoices):
        PENDING = "pending", "Chờ xử lý"
        PROCESSING = "processing", "Đang xử lý"
        COMPLETED = "completed", "Hoàn thành"
        FAILED = "failed", "Thất bại"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="deletion_requests",
    )
    tiers = models.JSONField(help_text="List of data tier keys to delete")
    status = models.CharField(
        max_length=15,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING,
    )
    result_summary = models.JSONField(default=dict)
    requested_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "palp_data_deletion_request"
        ordering = ["-requested_at"]

    def __str__(self):
        username = self.user.username if self.user else "deleted"
        return f"Deletion [{','.join(self.tiers)}] by {username} ({self.status})"
