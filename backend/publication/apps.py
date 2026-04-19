from django.apps import AppConfig


class PublicationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "publication"
    verbose_name = "Model Cards, Datasheets, Reproducibility kits"
