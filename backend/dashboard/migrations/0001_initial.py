import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0001_initial"),
        ("curriculum", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Alert",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("severity", models.CharField(choices=[("green", "On-track"), ("yellow", "Cần chú ý"), ("red", "Cần can thiệp")], max_length=10)),
                ("status", models.CharField(choices=[("active", "Đang mở"), ("dismissed", "Đã bỏ qua"), ("resolved", "Đã xử lý"), ("expired", "Hết hạn")], default="active", max_length=15)),
                ("trigger_type", models.CharField(choices=[("inactivity", "Không hoạt động"), ("retry_failure", "Thất bại nhiều lần"), ("milestone_lag", "Chậm tiến độ"), ("low_mastery", "Mastery thấp")], max_length=20)),
                ("reason", models.TextField()),
                ("evidence", models.JSONField(default=dict)),
                ("suggested_action", models.TextField(blank=True)),
                ("dismiss_reason_code", models.CharField(blank=True, choices=[("false_positive", "Báo nhầm"), ("student_leave", "SV nghỉ phép"), ("resolved_offline", "Xử lý ngoài hệ thống"), ("other", "Khác")], max_length=20)),
                ("dismiss_note", models.TextField(blank=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="alerts", to=settings.AUTH_USER_MODEL)),
                ("student_class", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="alerts", to="accounts.studentclass")),
                ("concept", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="alerts", to="curriculum.concept")),
                ("milestone", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="alerts", to="curriculum.milestone")),
                ("dismissed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="dismissed_alerts", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "palp_alert",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="alert",
            constraint=models.UniqueConstraint(
                condition=models.Q(status="active"),
                fields=("student", "trigger_type", "concept"),
                name="uq_alert_dedupe_active",
            ),
        ),
        migrations.AddIndex(
            model_name="alert",
            index=models.Index(fields=["student", "status", "severity"], name="idx_alert_student_status_sev"),
        ),
        migrations.AddIndex(
            model_name="alert",
            index=models.Index(fields=["student_class", "status", "-created_at"], name="idx_alert_class_status_created"),
        ),
        migrations.CreateModel(
            name="InterventionAction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action_type", models.CharField(choices=[("send_message", "Gửi tin nhắn"), ("suggest_task", "Gợi ý bài tập"), ("schedule_meeting", "Đặt lịch gặp")], max_length=20)),
                ("message", models.TextField(blank=True)),
                ("context", models.JSONField(default=dict)),
                ("follow_up_status", models.CharField(choices=[("pending", "Chờ phản hồi"), ("student_responded", "SV đã phản hồi"), ("resolved", "Đã xử lý"), ("no_response", "Không phản hồi")], default="pending", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("alert", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="actions", to="dashboard.alert")),
                ("lecturer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="intervention_actions", to=settings.AUTH_USER_MODEL)),
                ("targets", models.ManyToManyField(related_name="received_interventions", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "palp_intervention_action",
                "ordering": ["-created_at"],
            },
        ),
    ]
