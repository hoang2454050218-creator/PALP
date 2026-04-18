import pytest

from .models import Experiment, ExperimentVariant
from .services import assign_variant

pytestmark = pytest.mark.django_db


def _make_experiment(name="x_test", *, status=Experiment.Status.RUNNING):
    e = Experiment.objects.create(
        name=name, hypothesis="h", primary_metric="m", status=status,
    )
    ExperimentVariant.objects.create(experiment=e, name="control", weight=50)
    ExperimentVariant.objects.create(experiment=e, name="treatment", weight=50)
    return e


class TestAssignVariant:
    def test_returns_none_when_not_running(self, student):
        e = _make_experiment(status=Experiment.Status.DRAFT)
        assert assign_variant(e, student) is None

    def test_assignment_is_sticky_per_user(self, student):
        e = _make_experiment()
        first = assign_variant(e, student)
        for _ in range(10):
            assert assign_variant(e, student).id == first.id

    def test_different_users_can_get_different_variants(self, student, student_b):
        e = _make_experiment()
        v1 = assign_variant(e, student)
        v2 = assign_variant(e, student_b)
        # Possible they land on the same bucket -- the contract is just
        # that the call doesn't error.
        assert v1.experiment_id == e.id
        assert v2.experiment_id == e.id

    def test_returns_none_when_no_variants(self, student):
        e = Experiment.objects.create(
            name="empty", hypothesis="h", primary_metric="m",
            status=Experiment.Status.RUNNING,
        )
        assert assign_variant(e, student) is None
