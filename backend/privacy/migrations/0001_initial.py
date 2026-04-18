import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ConsentRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("purpose", models.CharField(choices=[("academic", "Dữ liệu học vụ lịch sử"), ("behavioral", "Dữ liệu hành vi học tập"), ("inference", "Dữ liệu suy luận (mastery, risk)")], max_length=20)),
                ("granted", models.BooleanField()),
                ("version", models.CharField(default="1.0", max_length=20)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="consent_records", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "palp_consent_record",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="consentrecord",
            index=models.Index(fields=["user", "purpose", "-created_at"], name="palp_consent_user_purpose_idx"),
        ),
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[("view", "Xem dữ liệu"), ("export", "Xuất dữ liệu"), ("delete", "Xóa dữ liệu"), ("anonymize", "Ẩn danh hóa"), ("consent_change", "Thay đổi đồng thuận"), ("incident", "Sự cố bảo mật")], max_length=20)),
                ("resource", models.CharField(max_length=200)),
                ("detail", models.JSONField(default=dict)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("request_id", models.UUIDField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audit_actions", to=settings.AUTH_USER_MODEL)),
                ("target_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audit_targets", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "palp_audit_log",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["actor", "-created_at"], name="palp_audit_actor_idx"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["target_user", "-created_at"], name="palp_audit_target_idx"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["action", "-created_at"], name="palp_audit_action_idx"),
        ),
        migrations.CreateModel(
            name="PrivacyIncident",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("severity", models.CharField(choices=[("low", "Thấp"), ("medium", "Trung bình"), ("high", "Cao"), ("critical", "Nghiêm trọng")], max_length=10)),
                ("status", models.CharField(choices=[("open", "Đang mở"), ("investigating", "Đang điều tra"), ("resolved", "Đã xử lý"), ("closed", "Đóng")], default="open", max_length=15)),
                ("title", models.CharField(max_length=300)),
                ("description", models.TextField()),
                ("affected_user_count", models.PositiveIntegerField(default=0)),
                ("affected_data_tiers", models.JSONField(default=list)),
                ("resolution", models.TextField(blank=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("sla_deadline", models.DateTimeField(help_text="48h from creation for response")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("reported_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reported_incidents", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "palp_privacy_incident",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="DataDeletionRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tiers", models.JSONField(help_text="List of data tier keys to delete")),
                ("status", models.CharField(choices=[("pending", "Chờ xử lý"), ("processing", "Đang xử lý"), ("completed", "Hoàn thành"), ("failed", "Thất bại")], default="pending", max_length=15)),
                ("result_summary", models.JSONField(default=dict)),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("user", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="deletion_requests", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "palp_data_deletion_request",
                "ordering": ["-requested_at"],
            },
        ),
    ]
