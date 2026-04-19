from django.apps import AppConfig


class BanditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "bandit"
    verbose_name = "Contextual Multi-Armed Bandit (Thompson Sampling)"
