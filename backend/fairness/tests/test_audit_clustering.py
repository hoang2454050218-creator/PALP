import pytest

from fairness.audit_clustering import audit_clustering
from fairness.models import FairnessAudit

pytestmark = pytest.mark.django_db


def _person(gender="M", region="urban"):
    return {"gender": gender, "region": region}


class TestAuditClustering:
    def test_passes_balanced_cluster(self):
        members = [_person("M"), _person("F"), _person("M"), _person("F")]
        population = [_person("M"), _person("F")] * 50
        audit = audit_clustering(
            target_name="balanced_cluster",
            cluster_members=members,
            total_population=population,
            attribute_getters={"gender": lambda m: m["gender"]},
        )
        assert audit.passed is True
        assert audit.violations == []

    def test_fails_when_concentration_exceeds_threshold(self):
        # Cluster: 9 F + 1 M (90% F), population 50/50
        members = [_person("F")] * 9 + [_person("M")]
        population = [_person("M")] * 50 + [_person("F")] * 50
        audit = audit_clustering(
            target_name="biased_cluster",
            cluster_members=members,
            total_population=population,
            attribute_getters={"gender": lambda m: m["gender"]},
        )
        assert audit.passed is False
        assert any(v["attr"] == "gender" and v["value"] == "F" for v in audit.violations)

    def test_does_not_fail_when_baseline_is_high(self):
        # Population already 80% F (e.g., nursing major), cluster 90% F -> not a violation
        members = [_person("F")] * 9 + [_person("M")]
        population = [_person("F")] * 80 + [_person("M")] * 20
        audit = audit_clustering(
            target_name="high_baseline_cluster",
            cluster_members=members,
            total_population=population,
            attribute_getters={"gender": lambda m: m["gender"]},
        )
        # Baseline F = 0.8 >= 0.5 default min_baseline -> NOT a violation
        assert audit.passed is True

    def test_multiple_attributes(self):
        members = [_person("F", "rural")] * 8 + [_person("M", "urban")] * 2
        population = (
            [_person("M", "urban")] * 30
            + [_person("M", "rural")] * 20
            + [_person("F", "urban")] * 30
            + [_person("F", "rural")] * 20
        )
        audit = audit_clustering(
            target_name="multi_attr_cluster",
            cluster_members=members,
            total_population=population,
            attribute_getters={
                "gender": lambda m: m["gender"],
                "region": lambda m: m["region"],
            },
        )
        # Cluster: F=80%, rural=80% -> both should violate (baseline F=50%, rural=40%)
        assert audit.passed is False
        attrs_in_violations = {v["attr"] for v in audit.violations}
        assert "gender" in attrs_in_violations
        assert "region" in attrs_in_violations

    def test_persists_to_audit_log(self):
        members = [_person("F")] * 5
        population = [_person("M")] * 50 + [_person("F")] * 50
        audit_clustering(
            target_name="persistence_cluster",
            cluster_members=members,
            total_population=population,
            attribute_getters={"gender": lambda m: m["gender"]},
        )
        assert FairnessAudit.objects.filter(
            target_name="persistence_cluster",
            kind=FairnessAudit.AuditKind.CLUSTERING,
        ).exists()
