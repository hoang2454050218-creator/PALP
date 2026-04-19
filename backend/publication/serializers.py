from __future__ import annotations

from rest_framework import serializers

from .models import Datasheet, ModelCard, ReproducibilityKit


class ModelCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelCard
        fields = [
            "id", "model_label", "title", "intended_use",
            "out_of_scope_uses", "training_data", "evaluation_data",
            "performance", "ethical_considerations", "caveats",
            "licence", "authors", "status",
            "created_at", "updated_at", "published_at",
        ]
        read_only_fields = [
            "id", "created_at", "updated_at", "published_at", "status",
        ]


class DatasheetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Datasheet
        fields = [
            "id", "dataset_key", "title", "motivation", "composition",
            "collection_process", "preprocessing", "uses",
            "distribution", "maintenance", "licence", "status",
            "created_at", "updated_at", "published_at",
        ]
        read_only_fields = [
            "id", "created_at", "updated_at", "published_at", "status",
        ]


class ReproducibilityKitSerializer(serializers.ModelSerializer):
    model_card_label = serializers.CharField(source="model_card.model_label", read_only=True)
    datasheet_key = serializers.CharField(source="datasheet.dataset_key", read_only=True)

    class Meta:
        model = ReproducibilityKit
        fields = [
            "id", "title", "model_card_label", "datasheet_key",
            "benchmark_run_id", "commit_hash", "seed", "notes",
            "created_at",
        ]
        read_only_fields = fields
