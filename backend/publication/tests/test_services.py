"""Model card / datasheet / repro-kit tests."""
from __future__ import annotations

import pytest

from publication.models import Datasheet, ModelCard, ReproducibilityKit
from publication.services import (
    bundle_repro_kit,
    draft_datasheet,
    draft_model_card,
    promote_model_card,
)


pytestmark = pytest.mark.django_db


class TestDraftModelCard:
    def test_creates_with_template_intent(self, admin_user):
        card = draft_model_card(model_label="bkt-baseline", requested_by=admin_user)
        assert card.status == ModelCard.Status.DRAFT
        assert "mastery" in card.intended_use.lower()

    def test_unknown_family_falls_back(self, admin_user):
        card = draft_model_card(model_label="random-other-model")
        assert "see description" in card.intended_use.lower()

    def test_idempotent_for_same_label(self, admin_user):
        a = draft_model_card(model_label="bkt-baseline")
        b = draft_model_card(model_label="bkt-baseline")
        assert a.id == b.id

    def test_uses_authors_default(self, settings):
        settings.PALP_PUBLICATION = {
            "AUTHORS_DEFAULT": [{"name": "Tester"}],
            "LICENCE_DEFAULT": "MIT",
        }
        card = draft_model_card(model_label="dkt-numpy")
        assert card.authors == [{"name": "Tester"}]
        assert card.licence == "MIT"


class TestPromoteModelCard:
    def test_draft_to_reviewed(self, admin_user):
        card = draft_model_card(model_label="risk-test")
        card = promote_model_card(card, target="reviewed")
        assert card.status == ModelCard.Status.REVIEWED

    def test_draft_to_published(self, admin_user):
        card = draft_model_card(model_label="risk-test-2")
        card = promote_model_card(card, target="published")
        assert card.status == ModelCard.Status.PUBLISHED
        assert card.published_at is not None

    def test_published_demotes_prior(self, admin_user):
        a = draft_model_card(model_label="risk-multi")
        a = promote_model_card(a, target="published")
        b = draft_model_card(model_label="risk-multi")
        b = promote_model_card(b, target="published")
        a.refresh_from_db()
        assert a.status == ModelCard.Status.REVIEWED
        assert b.status == ModelCard.Status.PUBLISHED

    def test_invalid_promotion_raises(self, admin_user):
        card = draft_model_card(model_label="risk-bad")
        try:
            promote_model_card(card, target="bogus")
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")


class TestDatasheetAndKit:
    def test_draft_datasheet_idempotent(self):
        a = draft_datasheet(dataset_key="ednet-kt1-synth")
        b = draft_datasheet(dataset_key="ednet-kt1-synth")
        assert a.id == b.id
        assert a.licence  # populated from settings default

    def test_bundle_repro_kit(self, admin_user):
        card = draft_model_card(model_label="dkt-numpy")
        sheet = draft_datasheet(dataset_key="ednet-kt1-synth")
        kit = bundle_repro_kit(
            model_card=card, datasheet=sheet,
            commit_hash="abc123", seed=99, requested_by=admin_user,
        )
        assert kit.commit_hash == "abc123"
        assert kit.seed == 99
        assert ReproducibilityKit.objects.filter(id=kit.id).exists()


class TestPublicationAPI:
    def test_admin_can_draft_and_promote(self, admin_user, admin_api):
        resp = admin_api.post(
            "/api/publication/model-cards/draft/",
            {"model_label": "dkt-numpy"},
            format="json",
        )
        assert resp.status_code == 201
        card_id = resp.json()["id"]
        promote = admin_api.post(
            f"/api/publication/model-cards/{card_id}/promote/",
            {"target": "published"},
            format="json",
        )
        assert promote.status_code == 200
        assert promote.json()["status"] == "published"

    def test_student_only_sees_published(self, admin_user, student, student_api):
        a = draft_model_card(model_label="risk-public")
        promote_model_card(a, target="published")
        draft_model_card(model_label="risk-private")
        resp = student_api.get("/api/publication/model-cards/")
        assert resp.status_code == 200
        body = resp.json()
        rows = body["results"] if isinstance(body, dict) else body
        labels = {row["model_label"] for row in rows}
        assert "risk-public" in labels
        assert "risk-private" not in labels

    def test_lecturer_can_create_kit(self, admin_user, lecturer_api):
        card = draft_model_card(model_label="dkt-numpy")
        sheet = draft_datasheet(dataset_key="ednet-kt1-synth")
        resp = lecturer_api.post(
            "/api/publication/repro-kits/create/",
            {"model_card_id": card.id, "datasheet_id": sheet.id, "commit_hash": "deadbeef"},
            format="json",
        )
        assert resp.status_code == 403  # only staff may create kits in this default
