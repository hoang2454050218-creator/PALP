from django.contrib import admin

from bandit.models import (
    BanditArm,
    BanditDecision,
    BanditExperiment,
    BanditPosterior,
    BanditReward,
    LinUCBArmState,
)


@admin.register(BanditExperiment)
class BanditExperimentAdmin(admin.ModelAdmin):
    list_display = ("key", "title", "status", "reward_window_minutes", "seed")
    list_filter = ("status",)
    search_fields = ("key", "title")


@admin.register(BanditArm)
class BanditArmAdmin(admin.ModelAdmin):
    list_display = ("id", "experiment", "key", "title", "is_enabled")
    list_filter = ("is_enabled", "experiment")
    raw_id_fields = ("experiment",)


@admin.register(BanditPosterior)
class BanditPosteriorAdmin(admin.ModelAdmin):
    list_display = (
        "arm", "context_key", "alpha", "beta",
        "pulls", "rewards_sum", "last_pulled_at",
    )
    list_filter = ("context_key",)
    raw_id_fields = ("arm",)


@admin.register(BanditDecision)
class BanditDecisionAdmin(admin.ModelAdmin):
    list_display = (
        "id", "experiment", "arm", "user",
        "context_key", "sampled_value", "decided_at",
    )
    raw_id_fields = ("experiment", "arm", "user")


@admin.register(BanditReward)
class BanditRewardAdmin(admin.ModelAdmin):
    list_display = ("id", "decision", "value", "recorded_at")
    raw_id_fields = ("decision",)


@admin.register(LinUCBArmState)
class LinUCBArmStateAdmin(admin.ModelAdmin):
    list_display = (
        "arm", "context_key", "dimension", "pulls",
        "rewards_sum", "last_pulled_at", "updated_at",
    )
    list_filter = ("context_key", "dimension")
    raw_id_fields = ("arm",)
    readonly_fields = ("updated_at", "last_pulled_at", "last_rewarded_at")
