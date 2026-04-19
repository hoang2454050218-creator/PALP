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
    # Phase 1D — context-aware BKT v2 mastery posterior. Null until the
    # v2 engine has seen at least one attempt for this row, then updated
    # every submission alongside ``p_mastery``. Promotion to default
    # consumer happens after shadow deployment (mlops.shadow) shows the
    # v2 estimator beats v1 by the gate threshold.
    p_mastery_v2 = models.FloatField(null=True, blank=True)
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

    def save(self, **kwargs):
        super().save(**kwargs)
        from django.core.cache import cache
        cache.delete(f"mastery:{self.student_id}:{self.concept_id}")

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

    @property
    def progress_pct(self) -> float:
        """Completed concepts divided by total active concepts in the course.

        Always clamped to [0, 100] so consumers can rely on the invariant
        without defensively clamping themselves.
        """
        completed = len(self.concepts_completed or [])
        total = self.course.concepts.filter(is_active=True).count() if self.course_id else 0
        if total <= 0:
            return 0.0
        pct = (completed / total) * 100
        return max(0.0, min(100.0, round(pct, 2)))


class MetacognitiveJudgment(models.Model):
    """Confidence rating recorded immediately before submitting a task.

    Phase 1E of the v3 roadmap. Compares the student's pre-submission
    confidence (1-5 Likert) against the actual correctness of the
    attempt. The resulting ``calibration_error`` becomes the metacognitive
    dimension of the RiskScore composite (Phase 1F) and feeds the weekly
    "you tend to over/under-confident on this kind of task" coach
    feedback prompt.

    Grounded in:
      - Dunlosky & Metcalfe (2009) "Metacognition" (judgment of learning)
      - Hacker et al. (2008) "Test prediction and performance"
    """

    class JudgmentType(models.TextChoices):
        JOL = "JOL", "Judgment of Learning (sau học, trước test)"
        FOK = "FOK", "Feeling of Knowing (trước recall)"
        EOL = "EOL", "Ease of Learning (trước nhiệm vụ mới)"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="metacognitive_judgments",
    )
    task_attempt = models.OneToOneField(
        TaskAttempt,
        on_delete=models.CASCADE,
        related_name="metacognitive_judgment",
        null=True,
        blank=True,
        help_text="Linked once the attempt is recorded; nullable so judgments "
                  "made before submit can still be persisted optimistically.",
    )
    task = models.ForeignKey(
        "curriculum.MicroTask",
        on_delete=models.CASCADE,
        related_name="metacognitive_judgments",
    )
    confidence_pre = models.PositiveSmallIntegerField(
        help_text="Likert 1 (very unsure) to 5 (very sure) recorded before submit.",
    )
    actual_correct = models.BooleanField(null=True, blank=True)
    calibration_error = models.FloatField(
        null=True, blank=True,
        help_text="|normalised(confidence) - actual_correct| in [0,1]. "
                  "0 = perfectly calibrated.",
    )
    judgment_type = models.CharField(
        max_length=5,
        choices=JudgmentType.choices,
        default=JudgmentType.JOL,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_metacog_judgment"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(confidence_pre__gte=1) & models.Q(confidence_pre__lte=5),
                name="ck_metacog_confidence_1_5",
            ),
            models.CheckConstraint(
                condition=models.Q(calibration_error__isnull=True)
                | (models.Q(calibration_error__gte=0) & models.Q(calibration_error__lte=1)),
                name="ck_metacog_calibration_0_1",
            ),
        ]
        indexes = [
            models.Index(fields=["student", "-created_at"], name="idx_metacog_student"),
            models.Index(fields=["task", "judgment_type"], name="idx_metacog_task_type"),
        ]

    def __str__(self) -> str:
        verdict = "?" if self.actual_correct is None else ("✓" if self.actual_correct else "✗")
        return f"{self.student_id}@{self.task_id} confidence={self.confidence_pre} actual={verdict}"

    def compute_calibration_error(self) -> float | None:
        """Refresh + persist calibration_error from current fields.

        Confidence is normalised to [0,1] via (k-1)/4 so a 5-Likert maps to 1.0
        and 1-Likert maps to 0.0. Then the error is the absolute distance to
        the binary outcome.
        """
        if self.actual_correct is None:
            return None
        normalised = (self.confidence_pre - 1) / 4.0
        actual = 1.0 if self.actual_correct else 0.0
        self.calibration_error = round(abs(normalised - actual), 4)
        return self.calibration_error


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
