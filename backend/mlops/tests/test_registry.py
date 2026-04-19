import pytest

from mlops.models import ModelRegistry, ModelVersion
from mlops.registry import (
    PromotionError,
    promote,
    register_model,
    register_version,
    production_versions,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def registry(admin_user):
    return register_model("test-risk-score", ModelRegistry.ModelType.RISK_SCORE, owner=admin_user)


class TestRegisterModel:
    def test_creates_registry(self, admin_user):
        reg = register_model("foo", ModelRegistry.ModelType.BKT, owner=admin_user)
        assert reg.name == "foo"
        assert reg.model_type == ModelRegistry.ModelType.BKT
        assert reg.owner == admin_user

    def test_idempotent_same_type(self, admin_user):
        a = register_model("foo", ModelRegistry.ModelType.BKT, owner=admin_user)
        b = register_model("foo", ModelRegistry.ModelType.BKT, owner=admin_user)
        assert a.pk == b.pk

    def test_rejects_type_change(self, admin_user):
        register_model("foo", ModelRegistry.ModelType.BKT, owner=admin_user)
        with pytest.raises(ValueError, match="already exists with type"):
            register_model("foo", ModelRegistry.ModelType.DKT, owner=admin_user)


class TestRegisterVersion:
    def test_creates_in_training_status(self, registry):
        v = register_version(registry, "1.0.0", metrics={"auc": 0.78})
        assert v.status == ModelVersion.Status.TRAINING
        assert v.metrics_json == {"auc": 0.78}

    def test_unique_semver_per_registry(self, registry):
        register_version(registry, "1.0.0")
        with pytest.raises(Exception):  # IntegrityError
            register_version(registry, "1.0.0")


class TestPromote:
    def test_training_to_shadow_allowed(self, registry, admin_user):
        v = register_version(registry, "1.0.0")
        promote(v, ModelVersion.Status.SHADOW, by=admin_user)
        v.refresh_from_db()
        assert v.status == ModelVersion.Status.SHADOW
        assert v.promoted_by == admin_user
        assert v.promoted_at is not None

    def test_invalid_transition_raises(self, registry):
        v = register_version(registry, "1.0.0")
        with pytest.raises(PromotionError, match="Cannot promote"):
            promote(v, ModelVersion.Status.PRODUCTION)  # skip shadow/staging

    def test_production_requires_fairness_passed(self, registry):
        v = register_version(registry, "1.0.0", fairness_passed=False)
        promote(v, ModelVersion.Status.SHADOW)
        promote(v, ModelVersion.Status.STAGING)
        with pytest.raises(PromotionError, match="fairness gate"):
            promote(v, ModelVersion.Status.PRODUCTION)

    def test_production_demotes_existing_production(self, registry, admin_user):
        old = register_version(registry, "1.0.0", fairness_passed=True)
        promote(old, ModelVersion.Status.SHADOW)
        promote(old, ModelVersion.Status.STAGING)
        promote(old, ModelVersion.Status.PRODUCTION, by=admin_user)

        new = register_version(registry, "2.0.0", fairness_passed=True)
        promote(new, ModelVersion.Status.SHADOW)
        promote(new, ModelVersion.Status.STAGING)
        promote(new, ModelVersion.Status.PRODUCTION, by=admin_user)

        old.refresh_from_db()
        new.refresh_from_db()
        assert old.status == ModelVersion.Status.DEPRECATED
        assert new.status == ModelVersion.Status.PRODUCTION

    def test_bypass_gates_for_emergency_rollback(self, registry, admin_user):
        v = register_version(registry, "1.0.0", fairness_passed=False)
        promote(v, ModelVersion.Status.SHADOW)
        promote(v, ModelVersion.Status.STAGING)
        promote(v, ModelVersion.Status.PRODUCTION, by=admin_user, bypass_gates=True)
        v.refresh_from_db()
        assert v.status == ModelVersion.Status.PRODUCTION


class TestProductionVersions:
    def test_returns_only_production(self, registry, admin_user):
        a = register_version(registry, "1.0.0", fairness_passed=True)
        promote(a, ModelVersion.Status.SHADOW)
        promote(a, ModelVersion.Status.STAGING)
        promote(a, ModelVersion.Status.PRODUCTION, by=admin_user)

        b = register_version(registry, "1.1.0")
        promote(b, ModelVersion.Status.SHADOW)

        prods = list(production_versions())
        assert a in prods
        assert b not in prods
