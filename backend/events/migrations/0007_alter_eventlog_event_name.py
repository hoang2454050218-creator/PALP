# Adds the ETL_* event_name choices so analytics.etl.pipeline.audit_log calls
# pass validation in events.services.audit_log without polluting the event
# taxonomy.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0006_eventlog_palp_event_actor_ts_desc"),
    ]

    operations = [
        migrations.AlterField(
            model_name="eventlog",
            name="event_name",
            field=models.CharField(
                choices=[
                    ("session_started", "Bắt đầu phiên"),
                    ("session_ended", "Kết thúc phiên"),
                    ("assessment_completed", "Hoàn thành assessment"),
                    ("assess_answer", "Trả lời câu hỏi assessment"),
                    ("assess_complete", "Nộp bài assessment"),
                    ("assess_expired", "Hết giờ assessment"),
                    ("assess_resumed", "Tiếp tục assessment"),
                    ("micro_task_completed", "Hoàn thành micro-task"),
                    ("content_intervention", "Can thiệp nội dung"),
                    ("retry_triggered", "Retry triggered"),
                    ("gv_dashboard_viewed", "GV xem dashboard"),
                    ("gv_action_taken", "GV thực hiện can thiệp"),
                    ("alert_dismissed", "Bỏ qua cảnh báo"),
                    ("intervention_created", "Tạo can thiệp"),
                    ("wellbeing_nudge", "Nhắc nghỉ"),
                    ("wellbeing_nudge_shown", "Hiện nhắc nghỉ"),
                    ("wellbeing_nudge_accepted", "Chấp nhận nghỉ"),
                    ("wellbeing_nudge_dismissed", "Bỏ qua nhắc nghỉ"),
                    ("page_view", "Xem trang"),
                    ("etl_started", "ETL bắt đầu"),
                    ("etl_completed", "ETL hoàn thành"),
                    ("etl_failed", "ETL thất bại"),
                ],
                db_index=True,
                max_length=50,
            ),
        ),
    ]
