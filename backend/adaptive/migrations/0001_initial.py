import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("curriculum", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="MasteryState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("p_mastery", models.FloatField(default=0.3)),
                ("p_guess", models.FloatField(default=0.25)),
                ("p_slip", models.FloatField(default=0.10)),
                ("p_transit", models.FloatField(default=0.09)),
                ("attempt_count", models.PositiveIntegerField(default=0)),
                ("correct_count", models.PositiveIntegerField(default=0)),
                ("version", models.PositiveIntegerField(default=1)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mastery_states", to=settings.AUTH_USER_MODEL)),
                ("concept", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mastery_states", to="curriculum.concept")),
            ],
            options={
                "db_table": "palp_mastery_state",
            },
        ),
        migrations.AddConstraint(
            model_name="masterystate",
            constraint=models.UniqueConstraint(fields=("student", "concept"), name="uq_mastery_student_concept"),
        ),
        migrations.AddIndex(
            model_name="masterystate",
            index=models.Index(fields=["student", "-last_updated"], name="idx_mastery_student_updated"),
        ),
        migrations.CreateModel(
            name="TaskAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("score", models.FloatField(default=0)),
                ("max_score", models.FloatField(default=100)),
                ("duration_seconds", models.PositiveIntegerField(default=0)),
                ("hints_used", models.PositiveSmallIntegerField(default=0)),
                ("is_correct", models.BooleanField(default=False)),
                ("answer", models.JSONField(default=dict)),
                ("attempt_number", models.PositiveSmallIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="task_attempts", to=settings.AUTH_USER_MODEL)),
                ("task", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attempts", to="curriculum.microtask")),
            ],
            options={
                "db_table": "palp_task_attempt",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="taskattempt",
            index=models.Index(fields=["student", "task", "-created_at"], name="idx_attempt_student_task"),
        ),
        migrations.AddIndex(
            model_name="taskattempt",
            index=models.Index(fields=["student", "-created_at"], name="idx_attempt_student_recent"),
        ),
        migrations.CreateModel(
            name="ContentIntervention",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("intervention_type", models.CharField(choices=[("supplementary", "Nội dung bổ trợ"), ("difficulty_down", "Giảm độ khó"), ("difficulty_up", "Tăng độ khó"), ("retry_hint", "Gợi ý retry"), ("recovery", "Hồi phục")], max_length=20)),
                ("source_rule", models.CharField(max_length=100)),
                ("rule_version", models.CharField(default="v1.0", max_length=20)),
                ("p_mastery_at_trigger", models.FloatField()),
                ("mastery_before", models.FloatField(blank=True, null=True)),
                ("mastery_after", models.FloatField(blank=True, null=True)),
                ("explanation", models.JSONField(default=dict)),
                ("was_helpful", models.BooleanField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="interventions", to=settings.AUTH_USER_MODEL)),
                ("concept", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="interventions", to="curriculum.concept")),
                ("content", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="content_interventions", to="curriculum.supplementarycontent")),
            ],
            options={
                "db_table": "palp_content_intervention",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="StudentPathway",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("current_difficulty", models.IntegerField(default=2)),
                ("concepts_completed", models.JSONField(default=list)),
                ("milestones_completed", models.JSONField(default=list)),
                ("tasks_completed", models.JSONField(default=list)),
                ("difficulty_history", models.JSONField(default=list)),
                ("last_known_template_versions", models.JSONField(default=dict, help_text="Map of milestone_id -> last seen template_version")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pathways", to=settings.AUTH_USER_MODEL)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="student_pathways", to="curriculum.course")),
                ("current_concept", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="current_students", to="curriculum.concept")),
                ("current_milestone", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="current_students", to="curriculum.milestone")),
            ],
            options={
                "db_table": "palp_student_pathway",
            },
        ),
        migrations.AddConstraint(
            model_name="studentpathway",
            constraint=models.UniqueConstraint(fields=("student", "course"), name="uq_pathway_student_course"),
        ),
        migrations.CreateModel(
            name="PathwayOverride",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("override_type", models.CharField(choices=[("force_concept", "Chuyển concept"), ("override_difficulty", "Đổi độ khó"), ("cancel_intervention", "Hủy can thiệp hệ thống"), ("force_main_flow", "Đưa về luồng chính")], max_length=25)),
                ("reason", models.TextField()),
                ("parameters", models.JSONField(default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("applied_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pathway_overrides", to=settings.AUTH_USER_MODEL)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pathway_overrides", to="curriculum.course")),
                ("lecturer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="issued_overrides", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "palp_pathway_override",
                "ordering": ["-applied_at"],
            },
        ),
    ]
