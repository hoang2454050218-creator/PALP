"""DB-aware service + view tests."""
from __future__ import annotations

import pytest

from benchmarks.models import BenchmarkDataset, BenchmarkRun
from benchmarks.services import (
    ensure_default_datasets,
    list_predictors,
    run_benchmark,
)


pytestmark = pytest.mark.django_db


class TestEnsureDefaultDatasets:
    def test_creates_two(self):
        rows = ensure_default_datasets()
        assert len(rows) == 2
        keys = {r.key for r in rows}
        assert keys == {"ednet-kt1-synth", "assistments-2009-synth"}

    def test_idempotent(self):
        ensure_default_datasets()
        ensure_default_datasets()
        assert BenchmarkDataset.objects.count() == 2


class TestRunBenchmark:
    def test_baseline_global_succeeds(self):
        ds = ensure_default_datasets()[0]
        run = run_benchmark(ds, predictor="baseline_global", sample_size=80)
        assert run.status == BenchmarkRun.Status.SUCCESS
        assert run.results.count() == 3
        keys = {r.metric_key for r in run.results.all()}
        assert keys == {"auc", "rmse", "accuracy"}

    def test_unknown_predictor_persists_failed_run(self):
        ds = ensure_default_datasets()[0]
        try:
            run_benchmark(ds, predictor="bogus", sample_size=10)
        except ValueError:
            return
        raise AssertionError("Expected ValueError before persisting")

    def test_dataset_counters_update(self):
        ds = ensure_default_datasets()[0]
        run_benchmark(ds, predictor="baseline_global", sample_size=50)
        ds.refresh_from_db()
        assert ds.interactions >= 1


class TestPredictorRegistry:
    def test_lists_expected(self):
        names = set(list_predictors())
        assert {"baseline_global", "baseline_per_concept", "logistic_per_concept"} <= names


class TestRunBenchmarkAPI:
    def test_admin_can_trigger(self, admin_user, admin_api):
        ensure_default_datasets()
        resp = admin_api.post(
            "/api/benchmarks/run/",
            {"dataset": "ednet-kt1-synth", "predictor": "baseline_global", "sample_size": 60},
            format="json",
        )
        assert resp.status_code == 201, resp.content
        body = resp.json()
        assert body["status"] == "success"
        assert any(r["metric_key"] == "auc" for r in body["results"])

    def test_student_blocked(self, student, student_api):
        resp = student_api.get("/api/benchmarks/predictors/")
        assert resp.status_code in (401, 403)

    def test_lecturer_can_read(self, lecturer, lecturer_api):
        ensure_default_datasets()
        resp = lecturer_api.get("/api/benchmarks/datasets/")
        assert resp.status_code == 200
        assert len(resp.json()) >= 2
