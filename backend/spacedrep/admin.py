from django.contrib import admin

from spacedrep.models import ReviewItem, ReviewLog


@admin.register(ReviewItem)
class ReviewItemAdmin(admin.ModelAdmin):
    list_display = (
        "id", "student", "concept", "state",
        "stability", "difficulty",
        "due_at", "review_count", "lapse_count",
    )
    list_filter = ("state",)
    raw_id_fields = ("student", "concept")


@admin.register(ReviewLog)
class ReviewLogAdmin(admin.ModelAdmin):
    list_display = (
        "id", "item", "rating",
        "post_stability", "post_difficulty",
        "interval_days", "retrievability_at_review",
        "reviewed_at",
    )
    list_filter = ("rating",)
    raw_id_fields = ("item",)
