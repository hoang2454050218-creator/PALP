from django.db import models
from django.conf import settings


class Assessment(models.Model):
    course = models.ForeignKey("curriculum.Course", on_delete=models.CASCADE, related_name="assessments")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    time_limit_minutes = models.PositiveSmallIntegerField(default=15)
    passing_score = models.PositiveIntegerField(default=60)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_assessment"

    def __str__(self):
        return self.title


class AssessmentQuestion(models.Model):
    class QuestionType(models.TextChoices):
        MULTIPLE_CHOICE = "multiple_choice", "Trắc nghiệm"
        TRUE_FALSE = "true_false", "Đúng/Sai"
        DRAG_DROP = "drag_drop", "Kéo thả"

    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="questions")
    concept = models.ForeignKey("curriculum.Concept", on_delete=models.CASCADE, related_name="assessment_questions")
    question_type = models.CharField(max_length=20, choices=QuestionType.choices, default=QuestionType.MULTIPLE_CHOICE)
    text = models.TextField()
    options = models.JSONField(default=list, help_text="List of answer options")
    correct_answer = models.JSONField(help_text="Correct answer(s)")
    explanation = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    points = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "palp_assessment_question"
        ordering = ["order"]

    def __str__(self):
        return f"Q{self.order}: {self.text[:50]}"


class AssessmentSession(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "Đang làm"
        COMPLETED = "completed", "Hoàn thành"
        ABANDONED = "abandoned", "Bỏ dở"
        EXPIRED = "expired", "Hết giờ"

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assessment_sessions")
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="sessions")
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.IN_PROGRESS)
    version = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    total_score = models.FloatField(null=True, blank=True)
    total_time_seconds = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = "palp_assessment_session"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "assessment"],
                condition=models.Q(status="in_progress"),
                name="uq_one_active_session_per_student_assessment",
            ),
        ]
        indexes = [
            models.Index(
                fields=["student", "assessment", "status"],
                name="idx_session_student_assess_st",
            ),
        ]

    @property
    def deadline(self):
        from datetime import timedelta
        return self.started_at + timedelta(minutes=self.assessment.time_limit_minutes)

    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.deadline

    def __str__(self):
        return f"{self.student.username} - {self.assessment.title} ({self.status})"


class AssessmentResponse(models.Model):
    session = models.ForeignKey(AssessmentSession, on_delete=models.CASCADE, related_name="responses")
    question = models.ForeignKey(AssessmentQuestion, on_delete=models.CASCADE, related_name="responses")
    answer = models.JSONField()
    is_correct = models.BooleanField(default=False)
    time_taken_seconds = models.PositiveIntegerField(default=0)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_assessment_response"
        constraints = [
            models.UniqueConstraint(
                fields=["session", "question"],
                name="uq_response_session_question",
            ),
        ]


class LearnerProfile(models.Model):
    student = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="learner_profile")
    course = models.ForeignKey("curriculum.Course", on_delete=models.CASCADE, related_name="learner_profiles")
    assessment_session = models.ForeignKey(
        AssessmentSession, on_delete=models.SET_NULL, null=True, related_name="profiles"
    )
    overall_score = models.FloatField(default=0)
    initial_mastery = models.JSONField(default=dict, help_text="Concept-level mastery from assessment")
    strengths = models.JSONField(default=list)
    weaknesses = models.JSONField(default=list)
    recommended_start_concept = models.ForeignKey(
        "curriculum.Concept", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="recommended_learner_profiles",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_learner_profile"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                name="uq_learner_profile_student_course",
            ),
        ]

    def __str__(self):
        return f"Profile: {self.student.username} ({self.overall_score:.0f}%)"
