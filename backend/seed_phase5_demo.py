"""One-shot seeder for Phase 5 (DKT + KG + Memory) browser demo.

Builds on top of seed_north_star_demo + seed_peer_demo + seed_coach_demo.
Adds:

* DKT attempt log entries so the predictor has history.
* Prerequisite edge metadata so the root-cause walker has variation.
* Episodic + semantic + procedural memory rows so the "Coach nhớ gì
  về bạn" panel renders something interesting.
* Grants the v1.4 consent that the memory panel requires.
"""
import os
from datetime import timedelta

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "palp.settings.dev_sqlite")
django.setup()

from django.utils import timezone

from accounts.models import User
from coach_memory.models import (
    EpisodicMemory,
    ProceduralMemory,
    SemanticMemory,
)
from coach_memory.services import (
    record_strategy_outcome,
    upsert_semantic,
    write_episodic,
)
from curriculum.models import Concept, ConceptPrerequisite, Course
from dkt.services import import_attempt, predict_for_student
from knowledge_graph.models import PrerequisiteEdge
from privacy.constants import CONSENT_VERSION
from privacy.models import ConsentRecord


DEMO_USERNAME = "demo_student"


def main() -> None:
    student = User.objects.get(username=DEMO_USERNAME)

    # ---------- Consent (re-grant ALL purposes at the bumped version) ----------
    from privacy.constants import CONSENT_PURPOSES
    for purpose in CONSENT_PURPOSES.keys():
        ConsentRecord.objects.create(
            user=student, purpose=purpose, granted=True, version=CONSENT_VERSION,
        )

    # ---------- DKT attempt log ----------
    course = Course.objects.get(code="SBVL-DEMO")
    concepts = list(Concept.objects.filter(course=course).order_by("order"))
    if len(concepts) >= 4:
        c1, c2, c3, c4 = concepts[:4]
        # Wipe then rebuild for idempotence.
        from dkt.models import DKTAttemptLog
        DKTAttemptLog.objects.filter(student=student).delete()

        now = timezone.now()
        # Mixed history: weak on c1, strong on c4.
        pattern = [
            (c1, False), (c1, False), (c1, True), (c1, False), (c1, False),
            (c2, True), (c2, False), (c2, True),
            (c3, True), (c3, True),
            (c4, True), (c4, True), (c4, True), (c4, True), (c4, True),
        ]
        for i, (concept, ok) in enumerate(pattern):
            import_attempt(
                student=student,
                concept=concept,
                is_correct=ok,
                occurred_at=now - timedelta(hours=len(pattern) - i),
            )

        # Run predict to populate DKTPrediction rows.
        predict_for_student(student=student, top_k=None)

    # ---------- Knowledge Graph edge metadata ----------
    for edge in ConceptPrerequisite.objects.filter(concept__course=course):
        PrerequisiteEdge.objects.update_or_create(
            edge=edge,
            defaults={"strength": 0.85, "dependency_type": "required"},
        )

    # ---------- Coach memory ----------
    EpisodicMemory.objects.filter(student=student).delete()
    SemanticMemory.objects.filter(student=student).delete()
    ProceduralMemory.objects.filter(student=student).delete()

    upsert_semantic(
        student=student, key="career_goal", value="Backend developer",
        confidence=0.9, source="goals.career_goal",
    )
    upsert_semantic(
        student=student, key="preferred_explanation_style", value="step-by-step",
        confidence=0.7, source="coach.dialog",
    )
    upsert_semantic(
        student=student, key="time_of_day", value="evening",
        confidence=0.6, source="signals.session_pattern",
    )

    write_episodic(
        student=student, kind="breakthrough",
        summary="Hiểu ra cách tích phân biểu đồ nội lực sau worked example",
        detail={"concept_id": concepts[0].id if concepts else None},
        salience=0.85,
        occurred_at=timezone.now() - timedelta(days=2),
    )
    write_episodic(
        student=student, kind="struggle",
        summary="Vướng dấu chiều mô-men uốn ở bài tập 3",
        detail={"concept_id": concepts[1].id if len(concepts) > 1 else None},
        salience=0.6,
        occurred_at=timezone.now() - timedelta(days=4),
    )
    write_episodic(
        student=student, kind="reflection",
        summary="Phản tỉnh tuần: cần ôn ứng suất chính",
        detail={"week": "2026-04-13"},
        salience=0.7,
        occurred_at=timezone.now() - timedelta(days=1),
    )

    # Procedural: 3 strategies with varying effectiveness.
    for _ in range(4):
        record_strategy_outcome(
            student=student, strategy_key="spaced_practice", success=True,
        )
    record_strategy_outcome(
        student=student, strategy_key="spaced_practice", success=False,
    )
    for _ in range(2):
        record_strategy_outcome(
            student=student, strategy_key="worked_examples", success=True,
        )
    record_strategy_outcome(
        student=student, strategy_key="cramming", success=False,
    )
    for _ in range(2):
        record_strategy_outcome(
            student=student, strategy_key="cramming", success=False,
        )

    print("=" * 60)
    print(f"Phase 5 demo seed complete for {student.username}")
    print(f"  DKT attempts seeded: {len(pattern) if len(concepts) >= 4 else 0}")
    print(f"  Semantic memory: 3 rows")
    print(f"  Episodic memory: 3 rows")
    print(f"  Procedural memory: 3 strategies")
    print("=" * 60)


main()
