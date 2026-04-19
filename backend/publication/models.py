"""Publication artefact models — Phase 7 of v3 MAXIMAL.

Three artefacts publication-grade ML systems are expected to ship:

* **ModelCard** — Mitchell et al. 2019 "Model Cards for Model
  Reporting". One per (model, version): intended use, training data,
  performance breakdown, ethical considerations.
* **Datasheet** — Gebru et al. 2018 "Datasheets for Datasets". One
  per dataset: motivation, composition, collection, processing.
* **ReproducibilityKit** — bundle of model card + datasheet + seed +
  benchmark run id + code commit hash, ready for paper supplementary.

The structured payloads stay editable in the admin so a researcher
can polish the auto-generated draft before publication.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models


class ModelCard(models.Model):
    """One Model Card row — auto-drafted by ``services.draft_model_card``."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Bản nháp"
        REVIEWED = "reviewed", "Đã review"
        PUBLISHED = "published", "Đã xuất bản"

    model_label = models.SlugField(
        max_length=120,
        help_text="e.g. 'sakt-numpy@0.1.0' or 'risk-composite@v1'.",
    )
    title = models.CharField(max_length=240)
    intended_use = models.TextField()
    out_of_scope_uses = models.JSONField(default=list, blank=True)
    training_data = models.JSONField(
        default=dict, blank=True,
        help_text="{description, size, period, license, link}",
    )
    evaluation_data = models.JSONField(default=dict, blank=True)
    performance = models.JSONField(
        default=dict, blank=True,
        help_text="Per-metric: {auc, rmse, accuracy, fairness_per_group}",
    )
    ethical_considerations = models.TextField(blank=True)
    caveats = models.TextField(blank=True)
    licence = models.CharField(max_length=80, blank=True)
    authors = models.JSONField(default=list, blank=True)

    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="model_cards_authored",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "palp_publication_model_card"
        indexes = [
            models.Index(fields=["status", "-updated_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["model_label", "status"],
                condition=models.Q(status="published"),
                name="uq_model_card_published_label",
            ),
        ]

    def __str__(self) -> str:
        return f"ModelCard({self.model_label}, {self.status})"


class Datasheet(models.Model):
    """One Datasheet (Gebru et al.) row."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Bản nháp"
        REVIEWED = "reviewed", "Đã review"
        PUBLISHED = "published", "Đã xuất bản"

    dataset_key = models.SlugField(max_length=120)
    title = models.CharField(max_length=240)
    motivation = models.TextField()
    composition = models.JSONField(
        default=dict, blank=True,
        help_text="{record_kind, count, schema, sensitive_attributes, missingness}",
    )
    collection_process = models.TextField(blank=True)
    preprocessing = models.TextField(blank=True)
    uses = models.JSONField(default=list, blank=True)
    distribution = models.TextField(blank=True)
    maintenance = models.TextField(blank=True)
    licence = models.CharField(max_length=80, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="datasheets_authored",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "palp_publication_datasheet"
        indexes = [
            models.Index(fields=["status", "-updated_at"]),
        ]

    def __str__(self) -> str:
        return f"Datasheet({self.dataset_key}, {self.status})"


class ReproducibilityKit(models.Model):
    """Bundles model card + datasheet + benchmark run + commit hash."""

    title = models.CharField(max_length=240)
    model_card = models.ForeignKey(
        ModelCard,
        on_delete=models.PROTECT,
        related_name="repro_kits",
    )
    datasheet = models.ForeignKey(
        Datasheet,
        on_delete=models.PROTECT,
        related_name="repro_kits",
    )
    benchmark_run_id = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Loose pointer to benchmarks.BenchmarkRun.",
    )
    commit_hash = models.CharField(max_length=80, blank=True)
    seed = models.PositiveIntegerField(default=42)
    notes = models.TextField(blank=True)

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="repro_kits",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_publication_repro_kit"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"ReproKit({self.title})"
