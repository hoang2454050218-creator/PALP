"""DKT service-layer + view tests."""
from __future__ import annotations

import pytest

from dkt.models import DKTPrediction
from dkt.services import (
    history_for,
    import_attempt,
    predict_for_concept,
    predict_for_student,
)


pytestmark = pytest.mark.django_db


class TestHistoryFor:
    def test_empty_for_brand_new_student(self, student):
        assert history_for(student) == []

    def test_orders_chronologically(self, student, concepts):
        from django.utils import timezone
        from datetime import timedelta

        now = timezone.now()
        import_attempt(
            student=student, concept=concepts[0], is_correct=False,
            occurred_at=now - timedelta(hours=2),
        )
        import_attempt(
            student=student, concept=concepts[1], is_correct=True,
            occurred_at=now,
        )
        rows = history_for(student)
        assert [r.concept_id for r in rows] == [concepts[0].id, concepts[1].id]


class TestPredictForConcept:
    def test_persists_prediction(self, student, concepts):
        result = predict_for_concept(student=student, target_concept_id=concepts[0].id)
        assert isinstance(result.persisted, DKTPrediction)
        assert 0.0 <= result.persisted.p_correct_next <= 1.0

    def test_idempotent_within_same_version(self, student, concepts):
        a = predict_for_concept(student=student, target_concept_id=concepts[0].id)
        b = predict_for_concept(student=student, target_concept_id=concepts[0].id)
        assert a.persisted.id == b.persisted.id


class TestPredictForStudent:
    def test_returns_top_k_weakest(self, student, concepts):
        # Seed mixed history so the predictions are not all equal.
        import_attempt(student=student, concept=concepts[0], is_correct=True)
        import_attempt(student=student, concept=concepts[1], is_correct=False)

        results = predict_for_student(student=student, top_k=2)
        assert len(results) == 2
        # Sorted weakest-first.
        assert (
            results[0].persisted.p_correct_next
            <= results[1].persisted.p_correct_next
        )


class TestViews:
    def test_my_view_requires_student(self, lecturer_api):
        resp = lecturer_api.get("/api/dkt/me/")
        assert resp.status_code == 403

    def test_my_view_returns_predictions(self, student_api, student, concepts):
        import_attempt(student=student, concept=concepts[0], is_correct=True)
        resp = student_api.get("/api/dkt/me/")
        assert resp.status_code == 200
        assert "predictions" in resp.data
        assert len(resp.data["predictions"]) >= 1

    def test_predict_endpoint_validates_concept_id(self, student_api):
        resp = student_api.post("/api/dkt/predict/", {}, format="json")
        assert resp.status_code == 400

    def test_predict_endpoint_returns_prediction(self, student_api, concepts):
        resp = student_api.post(
            "/api/dkt/predict/", {"concept_id": concepts[0].id}, format="json",
        )
        assert resp.status_code == 200
        assert "p_correct_next" in resp.data
