import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="PilotReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("report_type", models.CharField(choices=[("weekly", "Tuần"), ("milestone", "Mốc báo cáo"), ("final", "Báo cáo cuối")], max_length=15)),
                ("week_number", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("kpi_data", models.JSONField(default=dict)),
                ("usage_data", models.JSONField(default=dict)),
                ("csat_data", models.JSONField(default=dict)),
                ("notes", models.TextField(blank=True)),
                ("generated_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "palp_pilot_report",
                "ordering": ["-generated_at"],
            },
        ),
        migrations.CreateModel(
            name="DataQualityLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source", models.CharField(max_length=100)),
                ("total_records", models.PositiveIntegerField()),
                ("missing_values", models.PositiveIntegerField(default=0)),
                ("outliers_detected", models.PositiveIntegerField(default=0)),
                ("records_cleaned", models.PositiveIntegerField(default=0)),
                ("quality_score", models.FloatField(default=0)),
                ("details", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "palp_data_quality_log",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ETLRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("run_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("input_file", models.CharField(max_length=500)),
                ("semester", models.CharField(max_length=20)),
                ("input_checksum", models.CharField(max_length=64)),
                ("output_checksum", models.CharField(blank=True, max_length=64)),
                ("schema_snapshot", models.JSONField(default=dict)),
                ("input_version", models.CharField(max_length=50)),
                ("output_version", models.CharField(blank=True, max_length=50)),
                ("status", models.CharField(choices=[("running", "Đang chạy"), ("success", "Thành công"), ("failed", "Thất bại"), ("rolled_back", "Đã rollback")], default="running", max_length=20)),
                ("total_records", models.PositiveIntegerField(default=0)),
                ("records_imported", models.PositiveIntegerField(default=0)),
                ("records_skipped", models.PositiveIntegerField(default=0)),
                ("missing_values_handled", models.PositiveIntegerField(default=0)),
                ("outliers_flagged", models.PositiveIntegerField(default=0)),
                ("duplicates_found", models.PositiveIntegerField(default=0)),
                ("columns_excluded", models.JSONField(default=list)),
                ("outlier_review_queue", models.JSONField(default=list)),
                ("error_message", models.TextField(blank=True)),
                ("report", models.JSONField(default=dict)),
                ("parameters", models.JSONField(default=dict)),
                ("random_seed", models.IntegerField(blank=True, null=True)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "db_table": "palp_etl_run",
                "ordering": ["-started_at"],
            },
        ),
    ]
