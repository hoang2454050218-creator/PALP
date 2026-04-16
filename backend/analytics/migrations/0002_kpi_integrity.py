import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("analytics", "0001_initial"),
    ]

    operations = [
        # -- KPIDefinition --
        migrations.CreateModel(
            name="KPIDefinition",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=50, unique=True)),
                ("name", models.CharField(max_length=200)),
                ("description", models.TextField()),
                ("unit", models.CharField(max_length=50)),
                ("target_value", models.FloatField()),
                ("target_direction", models.CharField(choices=[("increase", "Tăng"), ("decrease", "Giảm"), ("absolute", "Đạt ngưỡng")], max_length=10)),
                ("source_events", models.JSONField(default=list)),
                ("query_function", models.CharField(max_length=200)),
                ("query_sql", models.TextField(blank=True)),
                ("baseline_value", models.FloatField(blank=True, null=True)),
                ("baseline_locked_at", models.DateTimeField(blank=True, null=True)),
                ("baseline_period_start", models.DateTimeField(blank=True, null=True)),
                ("baseline_period_end", models.DateTimeField(blank=True, null=True)),
                ("intervention_period_start", models.DateTimeField(blank=True, null=True)),
                ("intervention_period_end", models.DateTimeField(blank=True, null=True)),
                ("is_locked", models.BooleanField(default=False)),
                ("current_version", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="owned_kpis", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "palp_kpi_definition",
                "ordering": ["code"],
            },
        ),
        # -- KPIVersion --
        migrations.CreateModel(
            name="KPIVersion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version", models.PositiveIntegerField()),
                ("definition_snapshot", models.JSONField()),
                ("change_reason", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("kpi", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="versions", to="analytics.kpidefinition")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "palp_kpi_version",
                "ordering": ["kpi", "-version"],
                "unique_together": {("kpi", "version")},
            },
        ),
        # -- KPILineageLog --
        migrations.CreateModel(
            name="KPILineageLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("week_number", models.PositiveSmallIntegerField()),
                ("class_id", models.PositiveIntegerField()),
                ("computed_value", models.FloatField()),
                ("event_count", models.PositiveIntegerField(default=0)),
                ("event_date_range", models.JSONField(default=dict)),
                ("sample_event_ids", models.JSONField(default=list)),
                ("computation_params", models.JSONField(default=dict)),
                ("data_quality_flags", models.JSONField(default=dict)),
                ("definition_version", models.PositiveIntegerField()),
                ("computed_at", models.DateTimeField(auto_now_add=True)),
                ("kpi", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lineage_logs", to="analytics.kpidefinition")),
                ("report", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="lineage_logs", to="analytics.pilotreport")),
            ],
            options={
                "db_table": "palp_kpi_lineage_log",
                "ordering": ["-computed_at"],
            },
        ),
        # -- PilotReport: add schema_version and kpi_definitions_snapshot --
        migrations.AddField(
            model_name="pilotreport",
            name="schema_version",
            field=models.CharField(default="1.0", max_length=20),
        ),
        migrations.AddField(
            model_name="pilotreport",
            name="kpi_definitions_snapshot",
            field=models.JSONField(default=dict),
        ),
    ]
