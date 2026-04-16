from django.db import models
from django.conf import settings


class WellbeingNudge(models.Model):
    class NudgeType(models.TextChoices):
        BREAK_REMINDER = "break_reminder", "Nhắc nghỉ giải lao"
        STRETCH = "stretch", "Nhắc vận động"
        HYDRATE = "hydrate", "Nhắc uống nước"

    class NudgeResponse(models.TextChoices):
        SHOWN = "shown", "Đã hiện"
        ACCEPTED = "accepted", "Chấp nhận"
        DISMISSED = "dismissed", "Bỏ qua"

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wellbeing_nudges")
    nudge_type = models.CharField(max_length=20, choices=NudgeType.choices)
    response = models.CharField(max_length=15, choices=NudgeResponse.choices, default=NudgeResponse.SHOWN)
    continuous_minutes = models.PositiveIntegerField(help_text="Minutes of continuous study before nudge")
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "palp_wellbeing_nudge"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["student", "-created_at"],
                name="idx_nudge_student_created",
            ),
        ]
