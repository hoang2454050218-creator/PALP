from django.db import models
from django.conf import settings


class MasteryState(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mastery_states")
    concept = models.ForeignKey("curriculum.Concept", on_delete=models.CASCADE, related_name="mastery_states")
    p_mastery = models.FloatField(default=0.3)
    p_guess = models.FloatField(default=0.25)
    p_slip = models.FloatField(default=0.10)
    p_transit = models.FloatField(default=0.09)
    attempt_count = models.PositiveIntegerField(default=0)
    correct_count = models.PositiveIntegerField(default=0)
    version = models.PositiveIntegerField(default=1)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_mastery_state"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "concept"],
                name="uq_mastery_student_concept",
            ),
        ]
        indexes = [
            models.Index(
                fields=["student", "-last_updated"],
                name="idx_mastery_student_updated",
            ),
        ]

    def __str__(self):
        return f"{self.student.username} | {self.concept.name}: P(L)={self.p_mastery:.2f}"

    @property
    def mastery_level(self):
        thresholds = settings.PALP_ADAPTIVE_THRESHOLDS
        if self.p_mastery >= thresholds["MASTERY_HIGH"]:
            return "solid"
        if self.p_mastery >= thresholds["MASTERY_LOW"]:
            return "developing"
        return "emerging"

    STUDENT_LABELS = {
        "solid": "Vững chắc",
        "developing": "Đang tiến bộ",
        "emerging": "Đang tìm hiểu",
    }

    @property
    def student_facing_label(self):
        return self.STUDENT_LABELS[self.mastery_level]


class TaskAttempt(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="task_attempts")
    task = models.ForeignKey("curriculum.MicroTask", on_delete=models.CASCADE, related_name="attempts")
    score = models.FloatField(default=0)
    max_score = models.FloatField(default=100)
    duration_seconds = models.PositiveIntegerField(default=0)
    hints_used = models.PositiveSmallIntegerField(default=0)
    is_correct = models.BooleanField(default=False)
    answer = models.JSONField(default=dict)
    attempt_number = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_task_attempt"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["student", "task", "-created_at"],
                name="idx_attempt_student_task",
            ),
            models.Index(
                fields=["student", "-created_at"],
                name="idx_attempt_student_recent",
            ),
        ]

    def __str__(self):
        return f"{self.student.username} | {self.task.title} (#{self.attempt_number})"


class ContentIntervention(models.Model):
    class InterventionType(models.TextChoices):
        SUPPLEMENTARY = "supplementary", "Nội dung bổ trợ"
        DIFFICULTY_DOWN = "difficulty_down", "Giảm độ khó"
        DIFFICULTY_UP = "difficulty_up", "Tăng độ khó"
        RETRY_HINT = "retry_hint", "Gợi ý retry"
        RECOVERY = "recovery", "Hồi phục"

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="interventions")
    concept = models.ForeignKey("curriculum.Concept", on_delete=models.CASCADE, related_name="interventions")
    intervention_type = models.CharField(max_length=20, choices=InterventionType.choices)
    source_rule = models.CharField(max_length=100)
    rule_version = models.CharField(max_length=20, default="v1.0")
    content = models.ForeignKey(
        "curriculum.SupplementaryContent", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="content_interventions",
    )
    p_mastery_at_trigger = models.FloatField()
    mastery_before = models.FloatField(null=True, blank=True)
    mastery_after = models.FloatField(null=True, blank=True)
    explanation = models.JSONField(default=dict)
    was_helpful = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_content_intervention"
        ordering = ["-created_at"]


class StudentPathway(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pathways")
    course = models.ForeignKey(
        "curriculum.Course", on_delete=models.CASCADE, related_name="student_pathways",
    )
    current_concept = models.ForeignKey(
        "curriculum.Concept", on_delete=models.SET_NULL, null=True, related_name="current_students"
    )
    current_milestone = models.ForeignKey(
        "curriculum.Milestone", on_delete=models.SET_NULL, null=True, related_name="current_students"
    )
    current_difficulty = models.IntegerField(default=2)
    concepts_completed = models.JSONField(default=list)
    milestones_completed = models.JSONField(default=list)
    tasks_completed = models.JSONField(default=list)
    difficulty_history = models.JSONField(default=list)
    last_known_template_versions = models.JSONField(
        default=dict,
        help_text="Map of milestone_id -> last seen template_version",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_student_pathway"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                name="uq_pathway_student_course",
            ),
        ]


class PathwayOverride(models.Model):
    class OverrideType(models.TextChoices):
        FORCE_CONCEPT = "force_concept", "Chuyển concept"
        OVERRIDE_DIFFICULTY = "override_difficulty", "Đổi độ khó"
        CANCEL_INTERVENTION = "cancel_intervention", "Hủy can thiệp hệ thống"
        FORCE_MAIN_FLOW = "force_main_flow", "Đưa về luồng chính"

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pathway_overrides")
    course = models.ForeignKey(
        "curriculum.Course", on_delete=models.CASCADE, related_name="pathway_overrides",
    )
    lecturer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="issued_overrides"
    )
    override_type = models.CharField(max_length=25, choices=OverrideType.choices)
    reason = models.TextField()
    parameters = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "palp_pathway_override"
        ordering = ["-applied_at"]

    def __str__(self):
        return f"{self.lecturer.username} -> {self.student.username}: {self.override_type}"
