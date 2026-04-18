import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class EventLog(models.Model):
    CURRENT_VERSION = "1.0"

    class EventName(models.TextChoices):
        SESSION_STARTED = "session_started", "Bắt đầu phiên"
        SESSION_ENDED = "session_ended", "Kết thúc phiên"
        ASSESSMENT_COMPLETED = "assessment_completed", "Hoàn thành assessment"
        ASSESS_ANSWER = "assess_answer", "Trả lời câu hỏi assessment"
        ASSESS_COMPLETE = "assess_complete", "Nộp bài assessment"
        ASSESS_EXPIRED = "assess_expired", "Hết giờ assessment"
        ASSESS_RESUMED = "assess_resumed", "Tiếp tục assessment"
        MICRO_TASK_COMPLETED = "micro_task_completed", "Hoàn thành micro-task"
        CONTENT_INTERVENTION = "content_intervention", "Can thiệp nội dung"
        RETRY_TRIGGERED = "retry_triggered", "Retry triggered"
        GV_DASHBOARD_VIEWED = "gv_dashboard_viewed", "GV xem dashboard"
        GV_ACTION_TAKEN = "gv_action_taken", "GV thực hiện can thiệp"
        ALERT_DISMISSED = "alert_dismissed", "Bỏ qua cảnh báo"
        INTERVENTION_CREATED = "intervention_created", "Tạo can thiệp"
        WELLBEING_NUDGE = "wellbeing_nudge", "Nhắc nghỉ"
        WELLBEING_NUDGE_SHOWN = "wellbeing_nudge_shown", "Hiện nhắc nghỉ"
        WELLBEING_NUDGE_ACCEPTED = "wellbeing_nudge_accepted", "Chấp nhận nghỉ"
        WELLBEING_NUDGE_DISMISSED = "wellbeing_nudge_dismissed", "Bỏ qua nhắc nghỉ"
        PAGE_VIEW = "page_view", "Xem trang"
        ETL_STARTED = "etl_started", "ETL bắt đầu"
        ETL_COMPLETED = "etl_completed", "ETL hoàn thành"
        ETL_FAILED = "etl_failed", "ETL thất bại"

    class ActorType(models.TextChoices):
        STUDENT = "student", "Sinh viên"
        LECTURER = "lecturer", "Giảng viên"
        ADMIN = "admin", "Quản trị"
        SYSTEM = "system", "Hệ thống"

    LEARNING_EVENTS = {
        EventName.ASSESSMENT_COMPLETED,
        EventName.MICRO_TASK_COMPLETED,
        EventName.CONTENT_INTERVENTION,
        EventName.RETRY_TRIGGERED,
    }

    CONFIRMATION_REQUIRED_EVENTS = {
        EventName.ASSESSMENT_COMPLETED,
        EventName.MICRO_TASK_COMPLETED,
        EventName.GV_ACTION_TAKEN,
    }

    event_name = models.CharField(max_length=50, choices=EventName.choices, db_index=True)
    event_version = models.CharField(max_length=10, default=CURRENT_VERSION)
    timestamp_utc = models.DateTimeField(default=timezone.now, db_index=True)
    client_timestamp = models.DateTimeField(null=True, blank=True)

    actor_type = models.CharField(max_length=15, choices=ActorType.choices, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="event_logs",
    )
    session_id = models.CharField(max_length=100, blank=True, db_index=True)

    course = models.ForeignKey(
        "curriculum.Course",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="event_logs",
    )
    student_class = models.ForeignKey(
        "accounts.StudentClass",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="event_logs",
    )
    device_type = models.CharField(max_length=30, blank=True)
    source_page = models.CharField(max_length=200, blank=True)
    request_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    idempotency_key = models.CharField(
        max_length=150, unique=True, null=True, blank=True,
    )

    concept = models.ForeignKey(
        "curriculum.Concept",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="event_logs",
    )
    task = models.ForeignKey(
        "curriculum.MicroTask",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="event_logs",
    )
    difficulty_level = models.SmallIntegerField(null=True, blank=True)
    attempt_number = models.SmallIntegerField(null=True, blank=True)
    mastery_before = models.FloatField(null=True, blank=True)
    mastery_after = models.FloatField(null=True, blank=True)
    intervention_reason = models.CharField(max_length=100, blank=True)

    confirmed_at = models.DateTimeField(null=True, blank=True)

    properties = models.JSONField(default=dict)

    class Meta:
        db_table = "palp_event_log"
        ordering = ["-timestamp_utc"]
        indexes = [
            models.Index(fields=["actor_type", "event_name", "timestamp_utc"]),
            models.Index(fields=["course", "event_name"]),
            models.Index(fields=["actor", "event_name", "timestamp_utc"]),
            models.Index(fields=["session_id", "timestamp_utc"]),
            # Hot-path index for early warning's "last activity per actor"
            # GROUP BY query in dashboard.services.compute_early_warnings.
            models.Index(
                fields=["actor", "-timestamp_utc"],
                name="palp_event_actor_ts_desc",
            ),
        ]

    def __str__(self):
        actor_name = self.actor.username if self.actor else self.actor_type
        return f"{actor_name}: {self.event_name} @ {self.timestamp_utc}"

    @property
    def is_learning_event(self) -> bool:
        return self.event_name in self.LEARNING_EVENTS

    @property
    def requires_confirmation(self) -> bool:
        return self.event_name in self.CONFIRMATION_REQUIRED_EVENTS
