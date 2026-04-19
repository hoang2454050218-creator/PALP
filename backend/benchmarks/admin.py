from __future__ import annotations

from django.contrib import admin

from .models import BenchmarkDataset, BenchmarkResult, BenchmarkRun


class BenchmarkResultInline(admin.TabularInline):
    model = BenchmarkResult
    extra = 0
    readonly_fields = ("metric_key", "value", "notes")
    can_delete = False


@admin.register(BenchmarkDataset)
class BenchmarkDatasetAdmin(admin.ModelAdmin):
    list_display = ("key", "source", "students", "concepts", "interactions", "updated_at")
    list_filter = ("source",)
    search_fields = ("key", "title", "license")
    readonly_fields = ("created_at", "updated_at")


@admin.register(BenchmarkRun)
class BenchmarkRunAdmin(admin.ModelAdmin):
    list_display = (
        "id", "dataset", "model_label", "model_family", "status",
        "sample_size", "started_at", "finished_at",
    )
    list_filter = ("status", "model_family", "dataset__source")
    search_fields = ("model_label", "dataset__key")
    readonly_fields = ("started_at", "finished_at", "requested_by")
    inlines = [BenchmarkResultInline]


@admin.register(BenchmarkResult)
class BenchmarkResultAdmin(admin.ModelAdmin):
    list_display = ("run", "metric_key", "value")
    list_filter = ("metric_key",)
