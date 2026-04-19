from django.apps import AppConfig


class PrivacyDpConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "privacy_dp"
    verbose_name = "Differential Privacy (Laplace + budget)"
