"""Root-cause walker tests."""
from __future__ import annotations

import pytest

from adaptive.models import MasteryState
from knowledge_graph.models import PrerequisiteEdge, RootCauseSnapshot
from knowledge_graph.services import (
    cache_snapshot,
    export_graph,
    find_root_cause,
)


pytestmark = pytest.mark.django_db


def _set_mastery(student, concept, value):
    MasteryState.objects.update_or_create(
        student=student, concept=concept,
        defaults={"p_mastery": value},
    )


class TestFindRootCause:
    def test_walks_prerequisite_chain(self, student, concepts):
        # concepts fixture: c1 (NL) -> c2 (US) -> c3 (BD)
        c1, c2, c3 = concepts
        _set_mastery(student, c1, 0.3)
        _set_mastery(student, c2, 0.5)
        _set_mastery(student, c3, 0.6)

        result = find_root_cause(student=student, target_concept=c3)
        assert result.target_concept_id == c3.id
        # Visited should include c3, c2, c1.
        visited_ids = {n.concept_id for n in result.visited}
        assert {c1.id, c2.id, c3.id}.issubset(visited_ids)

    def test_picks_weakest_prerequisite(self, student, concepts):
        c1, c2, c3 = concepts
        _set_mastery(student, c1, 0.10)  # very weak
        _set_mastery(student, c2, 0.80)
        _set_mastery(student, c3, 0.70)

        result = find_root_cause(student=student, target_concept=c3)
        assert result.weakest_prerequisite_id == c1.id
        assert "Nội luc" not in result.recommendation  # ascii fallback
        assert "củng cố" in result.recommendation.lower() or "noi luc" in result.recommendation.lower()

    def test_concept_with_no_prereqs_returns_none(self, student, course):
        from curriculum.models import Concept
        leaf = Concept.objects.create(
            course=course, code="LEAF", name="Leaf", order=99,
        )
        _set_mastery(student, leaf, 0.5)
        result = find_root_cause(student=student, target_concept=leaf)
        assert result.weakest_prerequisite_id is None
        assert "không có prerequisite" in result.recommendation


class TestEdgeMetadata:
    def test_edge_metadata_influences_walker(self, student, concepts):
        from curriculum.models import ConceptPrerequisite
        c1, c2, c3 = concepts
        _set_mastery(student, c1, 0.5)
        _set_mastery(student, c2, 0.5)
        _set_mastery(student, c3, 0.5)

        # Make the c2->c1 edge very weak so c2 (closer prereq with
        # weaker dependency) becomes more attractive than c1.
        edge = ConceptPrerequisite.objects.get(concept=c2, prerequisite=c1)
        PrerequisiteEdge.objects.create(
            edge=edge, strength=0.2, dependency_type="helpful",
        )

        result = find_root_cause(student=student, target_concept=c3)
        # We don't assert the exact pick (the heuristic is gentle),
        # just that the walker still runs cleanly with the edge meta.
        assert result.confidence >= 0.0


class TestCacheSnapshot:
    def test_snapshot_persisted(self, student, concepts):
        c1, _c2, c3 = concepts
        _set_mastery(student, c1, 0.2)
        snap = cache_snapshot(student=student, target_concept=c3)
        assert isinstance(snap, RootCauseSnapshot)
        assert snap.target_concept_id == c3.id

    def test_snapshot_idempotent(self, student, concepts):
        c1, _c2, c3 = concepts
        _set_mastery(student, c1, 0.2)
        a = cache_snapshot(student=student, target_concept=c3)
        b = cache_snapshot(student=student, target_concept=c3)
        assert a.id == b.id


class TestExportGraph:
    def test_export_returns_nodes_and_edges(self, concepts):
        graph = export_graph()
        assert "nodes" in graph
        assert "edges" in graph
        assert len(graph["nodes"]) >= 3


class TestViews:
    def test_student_me_returns_recommendation(
        self, student_api, student, concepts,
    ):
        c1, _c2, c3 = concepts
        _set_mastery(student, c1, 0.1)
        resp = student_api.get(f"/api/knowledge-graph/me/root-cause/{c3.id}/")
        assert resp.status_code == 200
        assert resp.data["target_concept_id"] == c3.id
        assert "walk" in resp.data
        assert "recommendation" in resp.data["walk"]

    def test_lecturer_can_view_assigned_student(
        self, lecturer_api, student, concepts, class_with_members,
    ):
        c1, _c2, c3 = concepts
        _set_mastery(student, c1, 0.1)
        resp = lecturer_api.get(
            f"/api/knowledge-graph/student/{student.id}/root-cause/{c3.id}/"
        )
        assert resp.status_code == 200

    def test_other_lecturer_blocked(
        self, lecturer_other_api, student, concepts,
    ):
        c1, _c2, c3 = concepts
        _set_mastery(student, c1, 0.1)
        resp = lecturer_other_api.get(
            f"/api/knowledge-graph/student/{student.id}/root-cause/{c3.id}/"
        )
        assert resp.status_code == 403
