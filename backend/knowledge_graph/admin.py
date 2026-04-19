from django.contrib import admin

from knowledge_graph.models import PrerequisiteEdge, RootCauseSnapshot


@admin.register(PrerequisiteEdge)
class PrerequisiteEdgeAdmin(admin.ModelAdmin):
    list_display = ("edge", "strength", "dependency_type", "updated_at")
    list_filter = ("dependency_type",)
    raw_id_fields = ("edge",)


@admin.register(RootCauseSnapshot)
class RootCauseSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "id", "student", "target_concept",
        "weakest_prerequisite", "confidence", "computed_at",
    )
    raw_id_fields = ("student", "target_concept", "weakest_prerequisite")
