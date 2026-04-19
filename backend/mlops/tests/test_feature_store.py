import pytest
from django.core.cache import cache

from mlops.feature_store import (
    get_online,
    get_online_batch,
    push_online,
    register_view,
)
from mlops.models import FeatureView

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


class TestRegisterView:
    def test_creates_view(self):
        view = register_view(
            "student.signal_session",
            entity="student",
            source_table="palp_signals_session",
            features=[{"name": "focus_minutes", "dtype": "float", "ttl_seconds": 300}],
            online_store_enabled=True,
        )
        assert view.name == "student.signal_session"
        assert view.online_store_enabled is True

    def test_re_registration_updates_features(self):
        register_view(
            "student.foo",
            entity="student",
            source_table="t",
            features=[{"name": "a"}],
        )
        register_view(
            "student.foo",
            entity="student",
            source_table="t",
            features=[{"name": "b"}],
        )
        view = FeatureView.objects.get(name="student.foo")
        names = {f["name"] for f in view.features_json}
        assert names == {"a", "b"}


class TestOnlineStore:
    def test_push_and_get_online(self):
        view = register_view(
            "student.foo",
            entity="student",
            source_table="t",
            features=[{"name": "x", "dtype": "float"}],
            online_store_enabled=True,
        )
        push_online(view, entity_id=42, values={"x": 1.5})
        assert get_online(view, 42) == {"x": 1.5}

    def test_returns_none_when_offline_only(self):
        view = register_view(
            "student.bar",
            entity="student",
            source_table="t",
            features=[{"name": "x"}],
            online_store_enabled=False,
        )
        push_online(view, 1, {"x": 1.0})
        assert get_online(view, 1) is None

    def test_get_online_batch(self):
        view = register_view(
            "student.batch",
            entity="student",
            source_table="t",
            features=[{"name": "x"}],
            online_store_enabled=True,
        )
        push_online(view, 1, {"x": 0.1})
        push_online(view, 2, {"x": 0.2})
        result = get_online_batch(view, [1, 2, 3])
        assert result == {1: {"x": 0.1}, 2: {"x": 0.2}, 3: None}

    def test_unknown_view_returns_none(self):
        assert get_online("does.not.exist", 1) is None
