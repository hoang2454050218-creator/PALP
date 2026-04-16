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
            name="Assessment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("time_limit_minutes", models.PositiveSmallIntegerField(default=15)),
                ("passing_score", models.PositiveIntegerField(default=60)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assessments", to="curriculum.course")),
            ],
            options={
                "db_table": "palp_assessment",
            },
        ),
        migrations.CreateModel(
            name="AssessmentQuestion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("question_type", models.CharField(choices=[("multiple_choice", "Trắc nghiệm"), ("true_false", "Đúng/Sai"), ("drag_drop", "Kéo thả")], default="multiple_choice", max_length=20)),
                ("text", models.TextField()),
                ("options", models.JSONField(default=list, help_text="List of answer options")),
                ("correct_answer", models.JSONField(help_text="Correct answer(s)")),
                ("explanation", models.TextField(blank=True)),
                ("order", models.PositiveIntegerField(default=0)),
                ("points", models.PositiveIntegerField(default=1)),
                ("assessment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="questions", to="assessment.assessment")),
                ("concept", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assessment_questions", to="curriculum.concept")),
            ],
            options={
                "db_table": "palp_assessment_question",
                "ordering": ["order"],
            },
        ),
        migrations.CreateModel(
            name="AssessmentSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("in_progress", "Đang làm"), ("completed", "Hoàn thành"), ("abandoned", "Bỏ dở"), ("expired", "Hết giờ")], default="in_progress", max_length=15)),
                ("version", models.PositiveIntegerField(default=0)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("total_score", models.FloatField(blank=True, null=True)),
                ("total_time_seconds", models.PositiveIntegerField(blank=True, null=True)),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assessment_sessions", to=settings.AUTH_USER_MODEL)),
                ("assessment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sessions", to="assessment.assessment")),
            ],
            options={
                "db_table": "palp_assessment_session",
            },
        ),
        migrations.AddConstraint(
            model_name="assessmentsession",
            constraint=models.UniqueConstraint(
                condition=models.Q(status="in_progress"),
                fields=("student", "assessment"),
                name="uq_one_active_session_per_student_assessment",
            ),
        ),
        migrations.AddIndex(
            model_name="assessmentsession",
            index=models.Index(fields=["student", "assessment", "status"], name="idx_session_student_assess_st"),
        ),
        migrations.CreateModel(
            name="AssessmentResponse",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("answer", models.JSONField()),
                ("is_correct", models.BooleanField(default=False)),
                ("time_taken_seconds", models.PositiveIntegerField(default=0)),
                ("answered_at", models.DateTimeField(auto_now_add=True)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="responses", to="assessment.assessmentsession")),
                ("question", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="responses", to="assessment.assessmentquestion")),
            ],
            options={
                "db_table": "palp_assessment_response",
            },
        ),
        migrations.AddConstraint(
            model_name="assessmentresponse",
            constraint=models.UniqueConstraint(fields=("session", "question"), name="uq_response_session_question"),
        ),
        migrations.CreateModel(
            name="LearnerProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("overall_score", models.FloatField(default=0)),
                ("initial_mastery", models.JSONField(default=dict, help_text="Concept-level mastery from assessment")),
                ("strengths", models.JSONField(default=list)),
                ("weaknesses", models.JSONField(default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("student", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="learner_profile", to=settings.AUTH_USER_MODEL)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="learner_profiles", to="curriculum.course")),
                ("assessment_session", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="profiles", to="assessment.assessmentsession")),
                ("recommended_start_concept", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="recommended_learner_profiles", to="curriculum.concept")),
            ],
            options={
                "db_table": "palp_learner_profile",
            },
        ),
        migrations.AddConstraint(
            model_name="learnerprofile",
            constraint=models.UniqueConstraint(fields=("student", "course"), name="uq_learner_profile_student_course"),
        ),
    ]
