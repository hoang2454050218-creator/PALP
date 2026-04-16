import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Course",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=20, unique=True)),
                ("name", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("credits", models.PositiveSmallIntegerField(default=3)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "palp_course",
            },
        ),
        migrations.CreateModel(
            name="Concept",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=30)),
                ("name", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="concepts", to="curriculum.course")),
            ],
            options={
                "db_table": "palp_concept",
                "ordering": ["order"],
            },
        ),
        migrations.AddConstraint(
            model_name="concept",
            constraint=models.UniqueConstraint(fields=("course", "code"), name="uq_concept_course_code"),
        ),
        migrations.CreateModel(
            name="ConceptPrerequisite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("concept", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="prerequisites", to="curriculum.concept")),
                ("prerequisite", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="required_by", to="curriculum.concept")),
            ],
            options={
                "db_table": "palp_concept_prerequisite",
            },
        ),
        migrations.AddConstraint(
            model_name="conceptprerequisite",
            constraint=models.UniqueConstraint(fields=("concept", "prerequisite"), name="uq_prereq_concept_prerequisite"),
        ),
        migrations.AddConstraint(
            model_name="conceptprerequisite",
            constraint=models.CheckConstraint(
                check=~models.Q(concept=models.F("prerequisite")),
                name="ck_prereq_no_self_loop",
            ),
        ),
        migrations.CreateModel(
            name="Milestone",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("order", models.PositiveIntegerField(default=0)),
                ("target_week", models.PositiveSmallIntegerField(help_text="Target completion week in the pilot")),
                ("template_version", models.PositiveIntegerField(default=1)),
                ("is_active", models.BooleanField(default=True)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="milestones", to="curriculum.course")),
                ("concepts", models.ManyToManyField(blank=True, related_name="milestones", to="curriculum.concept")),
            ],
            options={
                "db_table": "palp_milestone",
                "ordering": ["order"],
            },
        ),
        migrations.CreateModel(
            name="MicroTask",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("task_type", models.CharField(choices=[("quiz", "Trắc nghiệm"), ("short_answer", "Trả lời ngắn"), ("calculation", "Bài tính"), ("drag_drop", "Kéo thả"), ("scenario", "Tình huống")], default="quiz", max_length=20)),
                ("difficulty", models.IntegerField(choices=[(1, "Dễ"), (2, "Trung bình"), (3, "Khó")], default=2)),
                ("estimated_minutes", models.PositiveSmallIntegerField(default=5)),
                ("content", models.JSONField(default=dict, help_text="Task content including questions, options, answers")),
                ("max_score", models.PositiveIntegerField(default=100)),
                ("order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("milestone", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tasks", to="curriculum.milestone")),
                ("concept", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tasks", to="curriculum.concept")),
            ],
            options={
                "db_table": "palp_micro_task",
                "ordering": ["order"],
            },
        ),
        migrations.CreateModel(
            name="SupplementaryContent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("content_type", models.CharField(choices=[("text", "Giải thích"), ("image", "Hình ảnh"), ("video", "Video"), ("example", "Ví dụ minh họa"), ("formula", "Công thức")], max_length=20)),
                ("body", models.TextField()),
                ("media_url", models.URLField(blank=True)),
                ("difficulty_target", models.IntegerField(choices=[(1, "Dễ"), (2, "Trung bình"), (3, "Khó")], default=1)),
                ("order", models.PositiveIntegerField(default=0)),
                ("concept", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="supplementary_contents", to="curriculum.concept")),
            ],
            options={
                "db_table": "palp_supplementary_content",
                "ordering": ["order"],
            },
        ),
        migrations.CreateModel(
            name="Enrollment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("semester", models.CharField(max_length=10)),
                ("enrolled_at", models.DateTimeField(auto_now_add=True)),
                ("is_active", models.BooleanField(default=True)),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="enrollments", to="accounts.user")),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="enrollments", to="curriculum.course")),
                ("student_class", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="enrollments", to="accounts.studentclass")),
            ],
            options={
                "db_table": "palp_enrollment",
            },
        ),
        migrations.AddConstraint(
            model_name="enrollment",
            constraint=models.UniqueConstraint(fields=("student", "course", "semester"), name="uq_enrollment_student_course_semester"),
        ),
    ]
