import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("curriculum", "0001_initial"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="EventLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_name", models.CharField(
                    choices=[
                        ("session_started", "Bắt đầu phiên"),
                        ("session_ended", "Kết thúc phiên"),
                        ("assessment_completed", "Hoàn thành assessment"),
                        ("micro_task_completed", "Hoàn thành micro-task"),
                        ("content_intervention", "Can thiệp nội dung"),
                        ("retry_triggered", "Retry triggered"),
                        ("gv_dashboard_viewed", "GV xem dashboard"),
                        ("gv_action_taken", "GV thực hiện can thiệp"),
                        ("wellbeing_nudge", "Nhắc nghỉ"),
                        ("wellbeing_nudge_shown", "Hiện nhắc nghỉ"),
                        ("wellbeing_nudge_accepted", "Chấp nhận nghỉ"),
                        ("wellbeing_nudge_dismissed", "Bỏ qua nhắc nghỉ"),
                        ("page_view", "Xem trang"),
                    ],
                    db_index=True, max_length=50,
                )),
                ("event_version", models.CharField(default="1.0", max_length=10)),
                ("timestamp_utc", models.DateTimeField(db_index=True)),
                ("client_timestamp", models.DateTimeField(blank=True, null=True)),
                ("actor_type", models.CharField(
                    choices=[
                        ("student", "Sinh viên"),
                        ("lecturer", "Giảng viên"),
                        ("admin", "Quản trị"),
                        ("system", "Hệ thống"),
                    ],
                    db_index=True, max_length=15,
                )),
                ("session_id", models.CharField(blank=True, db_index=True, max_length=100)),
                ("device_type", models.CharField(blank=True, max_length=30)),
                ("source_page", models.CharField(blank=True, max_length=200)),
                ("request_id", models.UUIDField(db_index=True, default=uuid.uuid4)),
                ("idempotency_key", models.CharField(blank=True, max_length=150, null=True, unique=True)),
                ("difficulty_level", models.SmallIntegerField(blank=True, null=True)),
                ("attempt_number", models.SmallIntegerField(blank=True, null=True)),
                ("mastery_before", models.FloatField(blank=True, null=True)),
                ("mastery_after", models.FloatField(blank=True, null=True)),
                ("intervention_reason", models.CharField(blank=True, max_length=100)),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("properties", models.JSONField(default=dict)),
                ("actor", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="event_logs",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("concept", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="event_logs",
                    to="curriculum.concept",
                )),
                ("course", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="event_logs",
                    to="curriculum.course",
                )),
                ("student_class", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="event_logs",
                    to="accounts.studentclass",
                )),
                ("task", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="event_logs",
                    to="curriculum.microtask",
                )),
            ],
            options={
                "db_table": "palp_event_log",
                "ordering": ["-timestamp_utc"],
            },
        ),
        migrations.AddIndex(
            model_name="eventlog",
            index=models.Index(fields=["actor_type", "event_name", "timestamp_utc"], name="palp_event__actor_t_idx"),
        ),
        migrations.AddIndex(
            model_name="eventlog",
            index=models.Index(fields=["course", "event_name"], name="palp_event__course_idx"),
        ),
        migrations.AddIndex(
            model_name="eventlog",
            index=models.Index(fields=["actor", "event_name", "timestamp_utc"], name="palp_event__actor_ev_idx"),
        ),
        migrations.AddIndex(
            model_name="eventlog",
            index=models.Index(fields=["session_id", "timestamp_utc"], name="palp_event__session_idx"),
        ),
    ]
