"""Knowledge Graph extension models — Phase 5 of v3 MAXIMAL roadmap.

We extend the prerequisite graph with two additive concepts:

* **PrerequisiteEdge** — supplements ``curriculum.ConceptPrerequisite``
  with edge metadata (strength, dependency_type) WITHOUT modifying the
  base table. This keeps the base contract unchanged for existing code
  while letting the root-cause walker weight edges.
* **RootCauseSnapshot** — caches the latest root-cause analysis per
  (student, target_concept) so the lecturer dashboard doesn't re-walk
  the graph on every request.

The walker itself lives in ``knowledge_graph/services.py``.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models


class PrerequisiteEdge(models.Model):
    """Edge metadata that lives alongside ``curriculum.ConceptPrerequisite``.

    One ``PrerequisiteEdge`` per ``ConceptPrerequisite``. Existing code
    that ignores this table keeps working with binary prerequisite
    semantics; the root-cause walker uses ``strength`` and
    ``dependency_type`` for ranking.
    """

    class DependencyType(models.TextChoices):
        # Conceptual: B's understanding REQUIRES A's understanding.
        REQUIRED = "required", "Bắt buộc trước"
        # Skill chain: A is a useful but not strict precursor.
        HELPFUL = "helpful", "Hữu ích"
        # Notation / vocabulary alignment.
        NOTATION = "notation", "Ký hiệu / quy ước"
        # Domain context only.
        CONTEXT = "context", "Bối cảnh"

    edge = models.OneToOneField(
        "curriculum.ConceptPrerequisite",
        on_delete=models.CASCADE,
        related_name="kg_metadata",
    )
    strength = models.FloatField(
        default=0.7,
        help_text="0..1 strength of the dependency (higher = more critical).",
    )
    dependency_type = models.CharField(
        max_length=16,
        choices=DependencyType.choices,
        default=DependencyType.REQUIRED,
    )
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_kg_prerequisite_edge"

    def __str__(self) -> str:
        return f"KGEdge({self.edge_id}, {self.dependency_type}, s={self.strength:.2f})"


class RootCauseSnapshot(models.Model):
    """Cached output of the root-cause walker for one (student, target).

    Re-computed on demand or by the nightly batch when many lecturers
    are likely to look at the same students. Keeping the snapshot
    keeps the lecturer dashboard fast even when the graph has many
    nodes.
    """

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="root_cause_snapshots",
    )
    target_concept = models.ForeignKey(
        "curriculum.Concept",
        on_delete=models.CASCADE,
        related_name="root_cause_targets",
    )

    weakest_prerequisite = models.ForeignKey(
        "curriculum.Concept",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="root_cause_weakest_for",
    )
    walk_payload = models.JSONField(
        default=dict, blank=True,
        help_text=(
            "{'visited': [{concept_id, name, p_mastery, depth}],"
            " 'edges': [{from, to, strength, type}], 'recommendation': str}"
        ),
    )
    confidence = models.FloatField(default=0.0)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_kg_root_cause_snapshot"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "target_concept"],
                name="uq_root_cause_student_target",
            ),
        ]
        indexes = [
            models.Index(fields=["student", "-computed_at"]),
        ]

    def __str__(self) -> str:
        return (
            f"RootCause({self.student_id} → {self.target_concept_id}) "
            f"weakest={self.weakest_prerequisite_id}"
        )
