from django.db import models
from django.conf import settings


class Alert(models.Model):
    class Severity(models.TextChoices):
        GREEN = "green", "On-track"
        YELLOW = "yellow", "Cần chú ý"
        RED = "red", "Cần can thiệp"

    class AlertStatus(models.TextChoices):
        ACTIVE = "active", "Đang mở"
        DISMISSED = "dismissed", "Đã bỏ qua"
        RESOLVED = "resolved", "Đã xử lý"
        EXPIRED = "expired", "Hết hạn"

    class TriggerType(models.TextChoices):
        INACTIVITY = "inactivity", "Không hoạt động"
        RETRY_FAILURE = "retry_failure", "Thất bại nhiều lần"
        MILESTONE_LAG = "milestone_lag", "Chậm tiến độ"
        LOW_MASTERY = "low_mastery", "Mastery thấp"

    class DismissReason(models.TextChoices):
        FALSE_POSITIVE = "false_positive", "Báo nhầm"
        STUDENT_LEAVE = "student_leave", "SV nghỉ phép"
        RESOLVED_OFFLINE = "resolved_offline", "Xử lý ngoài hệ thống"
        OTHER = "other", "Khác"

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="alerts")
    student_class = models.ForeignKey(
        "accounts.StudentClass", on_delete=models.SET_NULL, null=True, related_name="alerts"
    )
    severity = models.CharField(max_length=10, choices=Severity.choices)
    status = models.CharField(max_length=15, choices=AlertStatus.choices, default=AlertStatus.ACTIVE)
    trigger_type = models.CharField(max_length=20, choices=TriggerType.choices)
    concept = models.ForeignKey(
        "curriculum.Concept", on_delete=models.SET_NULL, null=True, blank=True, related_name="alerts"
    )
    milestone = models.ForeignKey(
        "curriculum.Milestone", on_delete=models.SET_NULL, null=True, blank=True, related_name="alerts"
    )
    reason = models.TextField()
    evidence = models.JSONField(default=dict)
    suggested_action = models.TextField(blank=True)
    dismissed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="dismissed_alerts"
    )
    dismiss_reason_code = models.CharField(
        max_length=20, choices=DismissReason.choices, blank=True,
    )
    dismiss_note = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_alert"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "trigger_type", "concept"],
                condition=models.Q(status="active"),
                name="uq_alert_dedupe_active",
            ),
        ]
        indexes = [
            models.Index(
                fields=["student", "status", "severity"],
                name="idx_alert_student_status_sev",
            ),
            models.Index(
                fields=["student_class", "status", "-created_at"],
                name="idx_alert_class_status_created",
            ),
        ]

    @property
    def is_expired(self):
        if self.expires_at is None:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"[{self.severity}] {self.student.username}: {self.trigger_type}"


class InterventionAction(models.Model):
    class ActionType(models.TextChoices):
        SEND_MESSAGE = "send_message", "Gửi tin nhắn"
        SUGGEST_TASK = "suggest_task", "Gợi ý bài tập"
        SCHEDULE_MEETING = "schedule_meeting", "Đặt lịch gặp"

    class FollowUpStatus(models.TextChoices):
        PENDING = "pending", "Chờ phản hồi"
        STUDENT_RESPONDED = "student_responded", "SV đã phản hồi"
        RESOLVED = "resolved", "Đã xử lý"
        NO_RESPONSE = "no_response", "Không phản hồi"

    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name="actions")
    lecturer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="intervention_actions")
    action_type = models.CharField(max_length=20, choices=ActionType.choices)
    targets = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="received_interventions")
    message = models.TextField(blank=True)
    context = models.JSONField(default=dict)
    follow_up_status = models.CharField(
        max_length=20, choices=FollowUpStatus.choices, default=FollowUpStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_intervention_action"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.lecturer.username} -> {self.action_type} ({self.follow_up_status})"
