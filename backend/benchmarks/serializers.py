from __future__ import annotations

from rest_framework import serializers

from .models import BenchmarkDataset, BenchmarkResult, BenchmarkRun


class BenchmarkResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = BenchmarkResult
        fields = ["metric_key", "value", "notes"]


class BenchmarkRunSerializer(serializers.ModelSerializer):
    dataset_key = serializers.CharField(source="dataset.key", read_only=True)
    results = BenchmarkResultSerializer(many=True, read_only=True)

    class Meta:
        model = BenchmarkRun
        fields = [
            "id", "dataset_key", "model_label", "model_family",
            "seed", "sample_size", "hyperparameters", "notes",
            "status", "started_at", "finished_at", "results",
        ]
        read_only_fields = fields


class BenchmarkDatasetSerializer(serializers.ModelSerializer):
    runs = BenchmarkRunSerializer(many=True, read_only=True)

    class Meta:
        model = BenchmarkDataset
        fields = [
            "id", "key", "title", "source", "description", "license",
            "loader_path", "students", "concepts", "interactions",
            "runs", "created_at", "updated_at",
        ]
        read_only_fields = fields
