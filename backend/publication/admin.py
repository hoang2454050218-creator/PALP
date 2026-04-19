from __future__ import annotations

from django.contrib import admin

from .models import Datasheet, ModelCard, ReproducibilityKit


@admin.register(ModelCard)
class ModelCardAdmin(admin.ModelAdmin):
    list_display = ("model_label", "title", "status", "licence", "updated_at", "published_at")
    list_filter = ("status", "licence")
    search_fields = ("model_label", "title")
    readonly_fields = ("created_at", "updated_at", "published_at")


@admin.register(Datasheet)
class DatasheetAdmin(admin.ModelAdmin):
    list_display = ("dataset_key", "title", "status", "licence", "updated_at", "published_at")
    list_filter = ("status",)
    search_fields = ("dataset_key", "title")
    readonly_fields = ("created_at", "updated_at", "published_at")


@admin.register(ReproducibilityKit)
class ReproducibilityKitAdmin(admin.ModelAdmin):
    list_display = ("title", "model_card", "datasheet", "benchmark_run_id", "commit_hash", "created_at")
    search_fields = ("title", "model_card__model_label", "datasheet__dataset_key", "commit_hash")
    readonly_fields = ("created_at",)
