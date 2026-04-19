"""
Direction Engine models — 3-tier goal hierarchy + Zimmerman SRL artefacts.

Hierarchy (loose foreign-key parenting; a student can skip levels):
  CareerGoal      6-12 months     "Tôi muốn làm backend dev"
  SemesterGoal    4-5 months      "Hoàn thành SBVL với mastery >= 70%"
  WeeklyGoal      7 days          "Học 5 buổi, mỗi buổi 60 phút"

Zimmerman SRL 3-phase support:
  Forethought   StrategyPlan + TimeEstimate (set BEFORE the work)
  Performance   linked to signals.SignalSession + adaptive.TaskAttempt
  Self-Reflection  GoalReflection + EffortRating + StrategyEffectiveness

Grounded in:
  - Zimmerman 2002 "Becoming a self-regulated learner"
  - Pintrich 2004 "A Conceptual Framework for Assessing Motivation and SRL"
  - Deci & Ryan 2017 SDT (autonomy/competence/relatedness)
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class CareerGoal(models.Model):
    """Long-horizon (6-12 month) career or learning direction.

    Free-form ``label`` so the student isn't trapped by an enum; the
    optional ``category`` slot lets us slice analytics without forcing
    a taxonomy on the user.
    """

    class Category(models.TextChoices):
        SOFTWARE_BACKEND = "software_backend", "Backend dev"
        SOFTWARE_FRONTEND = "software_frontend", "Frontend dev"
        SOFTWARE_FULLSTACK = "software_fullstack", "Full-stack dev"
        DATA = "data", "Data / Analytics"
        AI_ML = "ai_ml", "AI / ML"
        DEVOPS = "devops", "DevOps / SRE"
        SECURITY = "security", "Cybersecurity"
        ENGINEERING = "engineering", "Kỹ thuật khác"
        ACADEMIA = "academia", "Sau đại học / Nghiên cứu"
        OTHER = "other", "Khác"

    student = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="career_goal",
    )
    label = models.CharField(max_length=160)
    category = models.CharField(
        max_length=30, choices=Category.choices, default=Category.OTHER,
    )
    horizon_months = models.PositiveSmallIntegerField(default=12)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_goal_career"
        verbose_name = "Career goal"
        verbose_name_plural = "Career goals"

    def __str__(self) -> str:
        return f"{self.student_id}: {self.label}"


class SemesterGoal(models.Model):
    """Per-course semester goal.

    Anchored to a ``Course`` so a student taking 5 courses has 5
    distinct semester goals; ``mastery_target`` is the headline number
    the North Star "Đi về đâu" panel renders.
    """

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="semester_goals",
    )
    course = models.ForeignKey(
        "curriculum.Course",
        on_delete=models.CASCADE,
        related_name="semester_goals",
    )
    semester = models.CharField(
        max_length=10,
        help_text="Free-form semester id (e.g. '2026S1') consistent with curriculum.Enrollment.",
    )
    mastery_target = models.FloatField(
        default=0.70,
        help_text="Target average composite mastery for this course (0..1).",
    )
    completion_target_pct = models.PositiveSmallIntegerField(
        default=80,
        help_text="Target % of milestones completed by end of semester.",
    )
    intent = models.TextField(
        blank=True,
        help_text="Free-form motivation / why this matters to the student.",
    )
    started_at = models.DateField(default=timezone.localdate)
    target_end = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_goal_semester"
        ordering = ["-started_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course", "semester"],
                name="uq_semester_goal_student_course_semester",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student_id}@{self.course_id} {self.semester}: target {self.mastery_target:.0%}"


class WeeklyGoal(models.Model):
    """Concrete weekly target — Forethought-phase artefact.

    The student commits to a focus_minutes target and an optional list of
    concepts to cover. ``goals.drift_detector`` runs every 6h to compare
    ``target_minutes`` against the student's actual ``signals.SignalSession``
    focus output.
    """

    class Status(models.TextChoices):
        PLANNED = "planned", "Đã lên kế hoạch"
        IN_PROGRESS = "in_progress", "Đang thực hiện"
        COMPLETED = "completed", "Hoàn thành"
        DRIFTED = "drifted", "Lệch kế hoạch"
        ABANDONED = "abandoned", "Bỏ"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="weekly_goals",
    )
    semester_goal = models.ForeignKey(
        SemesterGoal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="weekly_goals",
    )
    week_start = models.DateField(
        help_text="Monday (Asia/Ho_Chi_Minh) of the week this goal targets.",
    )
    target_minutes = models.PositiveIntegerField(default=300)
    target_concept_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="Optional list of curriculum.Concept ids the student plans to cover.",
    )
    target_micro_task_count = models.PositiveSmallIntegerField(default=10)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PLANNED,
    )
    drift_pct_last_check = models.FloatField(
        null=True,
        blank=True,
        help_text="Most recent (target - actual) / target ratio. >0.4 trips drift.",
    )
    drift_last_checked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_goal_weekly"
        ordering = ["-week_start"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "week_start"],
                name="uq_weekly_goal_student_week",
            ),
            models.CheckConstraint(
                condition=models.Q(target_minutes__lte=10080),
                name="ck_weekly_goal_target_minutes_within_week",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student_id}@{self.week_start}: {self.target_minutes}m / {self.target_micro_task_count} tasks"


class StrategyPlan(models.Model):
    """Forethought-phase: which learning strategy will the student try.

    Categorical so the weekly reflection step can ask
    "did this strategy work better than last week's?" — required for the
    SRL self-reflection loop.
    """

    class Strategy(models.TextChoices):
        SPACED_PRACTICE = "spaced_practice", "Học dãn cách"
        DEEP_FOCUS_BLOCKS = "deep_focus_blocks", "Khối tập trung sâu"
        PEER_TEACHING = "peer_teaching", "Dạy bạn / được bạn dạy"
        WORKED_EXAMPLES = "worked_examples", "Đọc lời giải mẫu"
        SELF_EXPLANATION = "self_explanation", "Tự giải thích bằng lời"
        RETRIEVAL_PRACTICE = "retrieval_practice", "Truy hồi kiến thức"
        OTHER = "other", "Khác"

    weekly_goal = models.ForeignKey(
        WeeklyGoal,
        on_delete=models.CASCADE,
        related_name="strategy_plans",
    )
    strategy = models.CharField(max_length=30, choices=Strategy.choices)
    rationale = models.TextField(
        blank=True,
        help_text="Why the student picked this strategy this week (optional).",
    )
    predicted_minutes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_goal_strategy_plan"
        ordering = ["weekly_goal", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["weekly_goal", "strategy"],
                name="uq_strategy_plan_per_week",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.weekly_goal_id}: {self.strategy} ({self.predicted_minutes}m)"


class TimeEstimate(models.Model):
    """Forethought-phase: pre-task estimate of how long a unit of work will take.

    Pairs with the Performance-phase actual measurement
    (``signals.SignalSession.focus_minutes``) so we can chart the
    student's "calibration of effort" over time — the SRL counterpart of
    the metacognitive confidence calibration in Phase 1E.
    """

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="time_estimates",
    )
    weekly_goal = models.ForeignKey(
        WeeklyGoal,
        on_delete=models.CASCADE,
        related_name="time_estimates",
        null=True,
        blank=True,
    )
    concept = models.ForeignKey(
        "curriculum.Concept",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="time_estimates",
    )
    predicted_minutes = models.PositiveIntegerField()
    actual_minutes = models.PositiveIntegerField(null=True, blank=True)
    estimate_error_pct = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finalised_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "palp_goal_time_estimate"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["student", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.student_id}: predicted={self.predicted_minutes}m actual={self.actual_minutes}m"

    def finalise(self, actual_minutes: int) -> None:
        """Record actual time + compute error pct."""
        self.actual_minutes = max(0, int(actual_minutes))
        if self.predicted_minutes:
            self.estimate_error_pct = round(
                abs(self.predicted_minutes - self.actual_minutes) / self.predicted_minutes, 4
            )
        else:
            self.estimate_error_pct = None
        self.finalised_at = timezone.now()
        self.save(update_fields=["actual_minutes", "estimate_error_pct", "finalised_at"])


class GoalReflection(models.Model):
    """Self-Reflection-phase: weekly 3-question journal.

    The wording of the three prompts is intentionally locked in code so
    we can compare reflections across cohorts in research analyses.
    Free-form text is encrypted neither here nor at the API boundary —
    it's stored as plain text under ``behavioral_signals`` retention so
    the inference pipeline can read it locally; PII Guard catches it
    before any cloud LLM call.
    """

    weekly_goal = models.OneToOneField(
        WeeklyGoal,
        on_delete=models.CASCADE,
        related_name="reflection",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="goal_reflections",
    )
    week_start = models.DateField()

    learned_text = models.TextField(
        blank=True,
        help_text="Tuần này bạn học được gì? (max ~500 từ)",
    )
    struggle_text = models.TextField(
        blank=True,
        help_text="Đâu là khó khăn lớn nhất tuần này?",
    )
    next_priority_text = models.TextField(
        blank=True,
        help_text="Tuần sau bạn ưu tiên điều gì?",
    )

    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_goal_reflection"
        ordering = ["-week_start"]
        indexes = [
            models.Index(fields=["student", "-week_start"]),
        ]

    def __str__(self) -> str:
        return f"{self.student_id}@{self.week_start} reflection"


class EffortRating(models.Model):
    """Self-Reflection-phase: 1-5 perceived effort rating.

    Different from ``MetacognitiveJudgment`` (which measures confidence
    pre-submission). EffortRating is a post-week summary — "looking
    back, how hard did I try" — and is the core SRL self-evaluation
    component (Zimmerman 2008).
    """

    weekly_goal = models.OneToOneField(
        WeeklyGoal,
        on_delete=models.CASCADE,
        related_name="effort_rating",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="effort_ratings",
    )
    rating = models.PositiveSmallIntegerField(
        help_text="Likert 1 (very low effort) to 5 (very high effort)",
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_goal_effort_rating"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name="ck_effort_rating_1_5",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student_id}@{self.weekly_goal_id}: effort={self.rating}"


class StrategyEffectiveness(models.Model):
    """Self-Reflection-phase: did the chosen strategy work?

    Joined back to ``StrategyPlan`` so we can compare predicted vs
    perceived effectiveness over time. Inputs are subjective (Likert
    1-5), but combined with mastery delta they support a decent signal
    for "this student responds well to spaced practice".
    """

    strategy_plan = models.OneToOneField(
        StrategyPlan,
        on_delete=models.CASCADE,
        related_name="effectiveness",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="strategy_effectiveness_ratings",
    )
    rating = models.PositiveSmallIntegerField(
        help_text="Likert 1 (didn't help) to 5 (very effective)",
    )
    will_repeat = models.BooleanField(default=False)
    note = models.TextField(blank=True)
    mastery_delta = models.FloatField(
        null=True,
        blank=True,
        help_text="Composite mastery change observed during the week (filled by service).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_goal_strategy_effectiveness"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name="ck_strategy_effectiveness_rating_1_5",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.strategy_plan_id}: rating={self.rating}"
