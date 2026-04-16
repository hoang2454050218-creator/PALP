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
            name="WellbeingNudge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nudge_type", models.CharField(choices=[("break_reminder", "Nhắc nghỉ giải lao"), ("stretch", "Nhắc vận động"), ("hydrate", "Nhắc uống nước")], max_length=20)),
                ("response", models.CharField(choices=[("shown", "Đã hiện"), ("accepted", "Chấp nhận"), ("dismissed", "Bỏ qua")], default="shown", max_length=15)),
                ("continuous_minutes", models.PositiveIntegerField(help_text="Minutes of continuous study before nudge")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="wellbeing_nudges", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "palp_wellbeing_nudge",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="wellbeingnudge",
            index=models.Index(fields=["student", "-created_at"], name="idx_nudge_student_created"),
        ),
    ]
