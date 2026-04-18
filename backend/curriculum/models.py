from django.db import models


class Course(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    credits = models.PositiveSmallIntegerField(default=3)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_course"

    def __str__(self):
        return f"{self.code} - {self.name}"


class Enrollment(models.Model):
    student = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    student_class = models.ForeignKey(
        "accounts.StudentClass", on_delete=models.SET_NULL, null=True, related_name="enrollments"
    )
    semester = models.CharField(max_length=10)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "palp_enrollment"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course", "semester"],
                name="uq_enrollment_student_course_semester",
            ),
        ]


class Concept(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="concepts")
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "palp_concept"
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "code"],
                name="uq_concept_course_code",
            ),
            models.UniqueConstraint(
                fields=["course", "order"],
                name="uq_concept_course_order",
            ),
        ]

    def __str__(self):
        return f"{self.code}: {self.name}"


class ConceptPrerequisite(models.Model):
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="prerequisites")
    prerequisite = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="required_by")

    class Meta:
        db_table = "palp_concept_prerequisite"
        constraints = [
            models.UniqueConstraint(
                fields=["concept", "prerequisite"],
                name="uq_prereq_concept_prerequisite",
            ),
            models.CheckConstraint(
                check=~models.Q(concept=models.F("prerequisite")),
                name="ck_prereq_no_self_loop",
            ),
        ]


class Milestone(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="milestones")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    target_week = models.PositiveSmallIntegerField(help_text="Target completion week in the pilot")
    concepts = models.ManyToManyField(Concept, related_name="milestones", blank=True)
    template_version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "palp_milestone"
        ordering = ["order"]

    def __str__(self):
        return f"M{self.order}: {self.title}"


class MicroTask(models.Model):
    class DifficultyLevel(models.IntegerChoices):
        EASY = 1, "Dễ"
        MEDIUM = 2, "Trung bình"
        HARD = 3, "Khó"

    class TaskType(models.TextChoices):
        QUIZ = "quiz", "Trắc nghiệm"
        SHORT_ANSWER = "short_answer", "Trả lời ngắn"
        CALCULATION = "calculation", "Bài tính"
        DRAG_DROP = "drag_drop", "Kéo thả"
        SCENARIO = "scenario", "Tình huống"

    milestone = models.ForeignKey(Milestone, on_delete=models.CASCADE, related_name="tasks")
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    task_type = models.CharField(max_length=20, choices=TaskType.choices, default=TaskType.QUIZ)
    difficulty = models.IntegerField(choices=DifficultyLevel.choices, default=DifficultyLevel.MEDIUM)
    estimated_minutes = models.PositiveSmallIntegerField(default=5)
    content = models.JSONField(default=dict, help_text="Task content including questions, options, answers")
    max_score = models.PositiveIntegerField(default=100)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "palp_micro_task"
        ordering = ["order"]

    def __str__(self):
        return f"{self.title} (L{self.difficulty})"


class SupplementaryContent(models.Model):
    class ContentType(models.TextChoices):
        TEXT = "text", "Giải thích"
        IMAGE = "image", "Hình ảnh"
        VIDEO = "video", "Video"
        EXAMPLE = "example", "Ví dụ minh họa"
        FORMULA = "formula", "Công thức"

    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="supplementary_contents")
    title = models.CharField(max_length=200)
    content_type = models.CharField(max_length=20, choices=ContentType.choices)
    body = models.TextField()
    media_url = models.URLField(blank=True)
    difficulty_target = models.IntegerField(
        choices=MicroTask.DifficultyLevel.choices,
        default=MicroTask.DifficultyLevel.EASY,
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "palp_supplementary_content"
        ordering = ["order"]

    def __str__(self):
        return self.title
