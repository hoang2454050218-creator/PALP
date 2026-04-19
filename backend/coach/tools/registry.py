"""Tool registry for the coach.

Strict whitelist per ``COACH_SAFETY_PLAYBOOK`` section 8:

* Every tool is READ-ONLY. There is no ``update_*`` or ``send_*``.
* Every tool validates that ``args["student_id"]`` (if present) belongs
  to the requesting user. Cross-student lookups are RBAC-rejected.
* Every tool returns a JSON-serialisable dict so the result can ride in
  the LLM context AND be persisted in the audit log.

The registry is data-only — the orchestrator handles the dispatch +
audit logging. This keeps the registry trivially easy to extend (add a
row, write a handler) without touching the safety pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ToolSpec:
    name: str
    description: str
    handler: Callable[[dict, Any], dict]
    arg_schema: dict  # JSON-schema-ish; we hand-validate to avoid the dep
    rbac_owner_only: bool = True


# ---------------------------------------------------------------------------
# Tool implementations (READ-ONLY)
# ---------------------------------------------------------------------------

def _get_mastery(args: dict, user) -> dict:
    from adaptive.models import MasteryState

    rows = (
        MasteryState.objects
        .filter(student=user)
        .select_related("concept")
        .order_by("-p_mastery")[:20]
    )
    return {
        "concepts": [
            {
                "concept_id": r.concept_id,
                "concept_name": r.concept.name,
                "p_mastery": round(r.p_mastery, 4),
                "attempts": r.attempt_count,
            }
            for r in rows
        ]
    }


def _get_pathway(args: dict, user) -> dict:
    from adaptive.models import StudentPathway

    pathway = (
        StudentPathway.objects
        .filter(student=user, is_active=True)
        .select_related("current_concept", "current_milestone")
        .first()
    )
    if not pathway:
        return {"pathway": None}
    return {
        "pathway": {
            "current_concept": pathway.current_concept.name if pathway.current_concept else None,
            "current_milestone": pathway.current_milestone.title if pathway.current_milestone else None,
            "current_difficulty": pathway.current_difficulty,
            "completed_milestones": len(pathway.milestones_completed or []),
            "completed_concepts": len(pathway.concepts_completed or []),
        }
    }


def _get_risk_score(args: dict, user) -> dict:
    from risk.scoring import compute_risk_score

    snap = compute_risk_score(user, persist=False)
    return {
        "composite": round(snap.composite, 2),
        "severity": snap.severity,
        "dimensions": {k: round(float(v), 4) for k, v in snap.dimensions.items()},
    }


def _get_weekly_goal(args: dict, user) -> dict:
    from goals.models import WeeklyGoal
    from goals.services import monday_of
    from django.utils import timezone

    week_start = monday_of(timezone.localdate())
    wg = (
        WeeklyGoal.objects
        .filter(student=user, week_start=week_start)
        .first()
    )
    if not wg:
        return {"weekly_goal": None}
    return {
        "weekly_goal": {
            "target_minutes": wg.target_minutes,
            "target_micro_task_count": wg.target_micro_task_count,
            "status": wg.status,
            "drift_pct": wg.drift_pct_last_check,
        }
    }


def _get_calibration_history(args: dict, user) -> dict:
    from adaptive.models import MetacognitiveJudgment

    rows = (
        MetacognitiveJudgment.objects
        .filter(student=user)
        .order_by("-created_at")[:20]
    )
    return {
        "judgments": [
            {
                "task_id": j.task_id,
                "predicted_confidence": j.predicted_confidence,
                "was_correct": j.was_correct,
                "calibration_error": j.calibration_error,
            }
            for j in rows
        ]
    }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

REGISTRY: dict[str, ToolSpec] = {
    "get_mastery": ToolSpec(
        name="get_mastery",
        description="Mức mastery hiện tại theo concept của chính sinh viên.",
        handler=_get_mastery,
        arg_schema={"type": "object", "properties": {}},
    ),
    "get_pathway": ToolSpec(
        name="get_pathway",
        description="Lộ trình học hiện tại của chính sinh viên.",
        handler=_get_pathway,
        arg_schema={"type": "object", "properties": {}},
    ),
    "get_risk_score": ToolSpec(
        name="get_risk_score",
        description="Composite risk score 5-dim của chính sinh viên.",
        handler=_get_risk_score,
        arg_schema={"type": "object", "properties": {}},
    ),
    "get_weekly_goal": ToolSpec(
        name="get_weekly_goal",
        description="Mục tiêu tuần hiện tại + drift của chính sinh viên.",
        handler=_get_weekly_goal,
        arg_schema={"type": "object", "properties": {}},
    ),
    "get_calibration_history": ToolSpec(
        name="get_calibration_history",
        description="Lịch sử metacognitive calibration của chính sinh viên.",
        handler=_get_calibration_history,
        arg_schema={"type": "object", "properties": {}},
    ),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def execute(name: str, args: dict, user) -> dict:
    """Dispatch a tool call. RBAC-fail if the args reference another student."""
    spec = REGISTRY.get(name)
    if spec is None:
        return {"error": "tool_not_allowed", "name": name}

    if not _validate_args(args, spec.arg_schema):
        return {"error": "invalid_args", "name": name}

    if spec.rbac_owner_only:
        target_id = args.get("student_id")
        if target_id is not None and int(target_id) != user.id:
            return {"error": "rbac_denied", "name": name}

    try:
        return {"name": name, "result": spec.handler(args, user)}
    except Exception as exc:  # pragma: no cover - defensive
        return {"error": "tool_execution_failed", "name": name, "detail": str(exc)}


def _validate_args(args: dict, schema: dict) -> bool:
    """Tiny inline validator — only checks that args is a dict.

    The full ``jsonschema`` dependency is optional; for the small,
    object-only schemas we ship today the inline check is enough. As
    soon as we have nested schemas the orchestrator can swap in the
    real validator without touching the tools.
    """
    if not isinstance(args, dict):
        return False
    expected_type = schema.get("type")
    if expected_type and expected_type != "object":
        return False
    return True
