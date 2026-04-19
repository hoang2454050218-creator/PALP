"""Root-cause walker — find the weakest prerequisite in the dependency chain.

Problem: lecturer (or coach) sees that student S struggles on concept
``T``. The naive answer is "study T more". The right answer is often
"go fix prerequisite ``P`` whose mastery is the bottleneck for T".

Algorithm (BFS over the prerequisite DAG):

1. Start from ``T``.
2. For each prerequisite ``P`` of the current frontier, look up
   * ``p_mastery(student, P)``  (from ``adaptive.MasteryState``),
   * edge strength + dependency_type weight (from
     ``knowledge_graph.PrerequisiteEdge``; default if unset),
3. Stop when (a) we reach a leaf (no further prerequisites) or
   (b) we've walked ``MAX_DEPTH`` hops.
4. Return the prerequisite with the **lowest weighted score**
   (mastery * (1 - edge_weight)) — that is the bottleneck the student
   should fix first.

The walker is deterministic and cycle-safe (visited set).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from django.conf import settings
from django.db import transaction


MAX_DEPTH_DEFAULT = 4


@dataclass
class WalkNode:
    concept_id: int
    name: str
    p_mastery: float
    depth: int


@dataclass
class WalkEdge:
    from_concept: int
    to_concept: int
    strength: float
    dependency_type: str


@dataclass
class RootCauseResult:
    target_concept_id: int
    weakest_prerequisite_id: int | None
    weakest_score: float
    visited: list[WalkNode]
    edges: list[WalkEdge]
    recommendation: str
    confidence: float


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_root_cause(*, student, target_concept) -> RootCauseResult:
    """BFS the prerequisite DAG and return the bottleneck.

    Returns a ``RootCauseResult`` with the weakest prerequisite (or
    ``None`` if no prerequisites exist or the target is itself the
    weakest concept).
    """
    from curriculum.models import Concept, ConceptPrerequisite
    from adaptive.models import MasteryState

    max_depth = int(
        getattr(settings, "PALP_KG", {}).get("MAX_DEPTH", MAX_DEPTH_DEFAULT)
    )

    target = (
        Concept.objects.filter(pk=target_concept.pk).first()
        if hasattr(target_concept, "pk") else
        Concept.objects.filter(pk=target_concept).first()
    )
    if target is None:
        return RootCauseResult(
            target_concept_id=getattr(target_concept, "pk", target_concept),
            weakest_prerequisite_id=None,
            weakest_score=0.5,
            visited=[],
            edges=[],
            recommendation="target_concept_unknown",
            confidence=0.0,
        )

    mastery_map = dict(
        MasteryState.objects
        .filter(student=student)
        .values_list("concept_id", "p_mastery")
    )

    visited_ids: set[int] = {target.id}
    visited: list[WalkNode] = [
        WalkNode(
            concept_id=target.id,
            name=target.name,
            p_mastery=float(mastery_map.get(target.id, 0.5)),
            depth=0,
        )
    ]
    edges: list[WalkEdge] = []
    frontier: deque[tuple[int, int]] = deque([(target.id, 0)])
    weakest_id: int | None = None
    weakest_score = 1.0  # we're looking for the lowest score (bottleneck)

    while frontier:
        node_id, depth = frontier.popleft()
        if depth >= max_depth:
            continue

        prereq_rows = list(
            ConceptPrerequisite.objects
            .filter(concept_id=node_id)
            .select_related("prerequisite")
        )

        for row in prereq_rows:
            prereq = row.prerequisite
            edge_meta = getattr(row, "kg_metadata", None)
            strength = float(edge_meta.strength) if edge_meta else 0.7
            dependency_type = (
                edge_meta.dependency_type if edge_meta else "required"
            )
            edges.append(
                WalkEdge(
                    from_concept=node_id,
                    to_concept=prereq.id,
                    strength=strength,
                    dependency_type=dependency_type,
                )
            )

            if prereq.id not in visited_ids:
                visited_ids.add(prereq.id)
                p_mastery = float(mastery_map.get(prereq.id, 0.5))
                node = WalkNode(
                    concept_id=prereq.id,
                    name=prereq.name,
                    p_mastery=p_mastery,
                    depth=depth + 1,
                )
                visited.append(node)
                frontier.append((prereq.id, depth + 1))

                # Score = mastery * (1 - strength); stronger
                # dependency hurts more if the student is weak there.
                score = p_mastery + (1.0 - strength) * 0.2
                if score < weakest_score:
                    weakest_score = score
                    weakest_id = prereq.id

    confidence = min(1.0, len(visited_ids) / max(len(mastery_map), 1))

    if weakest_id is None:
        recommendation = (
            f"Concept '{target.name}' không có prerequisite trong đồ thị — "
            "nên ôn trực tiếp hoặc làm bài tập mức cơ bản hơn."
        )
    else:
        weakest_node = next(
            (n for n in visited if n.concept_id == weakest_id),
            None,
        )
        weakest_name = weakest_node.name if weakest_node else f"id={weakest_id}"
        weakest_mastery_pct = (
            int(round(weakest_node.p_mastery * 100)) if weakest_node else 0
        )
        recommendation = (
            f"Trước khi học '{target.name}', nên củng cố '{weakest_name}' "
            f"(mastery hiện tại ~{weakest_mastery_pct}%). Đây là tiền đề "
            "có ảnh hưởng lớn nhất tới khả năng nắm vững mục tiêu."
        )

    return RootCauseResult(
        target_concept_id=target.id,
        weakest_prerequisite_id=weakest_id,
        weakest_score=round(weakest_score, 4),
        visited=visited,
        edges=edges,
        recommendation=recommendation,
        confidence=round(confidence, 4),
    )


@transaction.atomic
def cache_snapshot(*, student, target_concept) -> "RootCauseSnapshot":
    """Run the walker + persist the result so dashboards stay fast."""
    from knowledge_graph.models import RootCauseSnapshot

    result = find_root_cause(student=student, target_concept=target_concept)
    snap, _ = RootCauseSnapshot.objects.update_or_create(
        student=student,
        target_concept_id=result.target_concept_id,
        defaults={
            "weakest_prerequisite_id": result.weakest_prerequisite_id,
            "walk_payload": {
                "visited": [n.__dict__ for n in result.visited],
                "edges": [e.__dict__ for e in result.edges],
                "recommendation": result.recommendation,
                "weakest_score": result.weakest_score,
            },
            "confidence": result.confidence,
        },
    )
    return snap


def export_graph() -> dict:
    """Dump the prerequisite graph for visualisation (read-only)."""
    from curriculum.models import Concept, ConceptPrerequisite

    nodes = list(
        Concept.objects.filter(is_active=True).values("id", "code", "name", "course_id")
    )
    edges = list(
        ConceptPrerequisite.objects.values(
            "concept_id", "prerequisite_id"
        )
    )

    edge_meta = {
        em.edge_id: em
        for em in _all_edge_metadata()
    }
    enriched_edges = [
        {
            "from": e["prerequisite_id"],
            "to": e["concept_id"],
            "strength": float(edge_meta[em_id].strength) if (em_id := _edge_pk_for(e)) and em_id in edge_meta else 0.7,
            "dependency_type": edge_meta[em_id].dependency_type
                if (em_id := _edge_pk_for(e)) and em_id in edge_meta
                else "required",
        }
        for e in edges
    ]
    return {"nodes": nodes, "edges": enriched_edges}


def _all_edge_metadata():
    from knowledge_graph.models import PrerequisiteEdge
    return list(PrerequisiteEdge.objects.all())


def _edge_pk_for(edge_row: dict) -> int | None:
    """Look up the ConceptPrerequisite PK for the (concept, prerequisite) pair.

    We don't have it in the projected dict so we accept the cost of a
    sub-query here. The graph export is admin-only / lecturer-only so
    the latency is fine.
    """
    from curriculum.models import ConceptPrerequisite
    return (
        ConceptPrerequisite.objects
        .filter(
            concept_id=edge_row["concept_id"],
            prerequisite_id=edge_row["prerequisite_id"],
        )
        .values_list("id", flat=True)
        .first()
    )
