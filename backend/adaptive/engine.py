"""
Bayesian Knowledge Tracing (BKT) engine for adaptive pathway decisions.

BKT models a learner's knowledge state as a hidden variable that transitions
from "not learned" to "learned" after each practice opportunity. The four
parameters per concept are:
  P(L0)  - prior probability of mastery
  P(T)   - probability of learning on each attempt
  P(G)   - probability of a correct guess when not mastered
  P(S)   - probability of a slip when mastered
"""
import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.db import transaction

from .models import MasteryState, ContentIntervention
from curriculum.models import Concept, SupplementaryContent
from events.emitter import emit_event
from events.metrics import ADAPTIVE_DECISION_DURATION
from events.models import EventLog

logger = logging.getLogger("palp")

THRESHOLDS = settings.PALP_ADAPTIVE_THRESHOLDS
BKT_DEFAULTS = settings.PALP_BKT_DEFAULTS

CACHE_TTL = 300


def _cache_key(student_id: int, concept_id: int) -> str:
    return f"mastery:{student_id}:{concept_id}"


def get_mastery_state(student_id: int, concept_id: int, *, for_update: bool = False) -> MasteryState:
    if not for_update:
        cached = cache.get(_cache_key(student_id, concept_id))
        if cached:
            return cached

    qs = MasteryState.objects.all()
    if for_update:
        qs = qs.select_for_update()

    state, _ = qs.get_or_create(
        student_id=student_id,
        concept_id=concept_id,
        defaults={
            "p_mastery": BKT_DEFAULTS["P_L0"],
            "p_guess": BKT_DEFAULTS["P_GUESS"],
            "p_slip": BKT_DEFAULTS["P_SLIP"],
            "p_transit": BKT_DEFAULTS["P_TRANSIT"],
        },
    )
    cache.set(_cache_key(student_id, concept_id), state, CACHE_TTL)
    return state


@transaction.atomic
def update_mastery(student_id: int, concept_id: int, is_correct: bool) -> MasteryState:
    cache.delete(_cache_key(student_id, concept_id))

    state = get_mastery_state(student_id, concept_id, for_update=True)
    p_l = state.p_mastery
    p_g = state.p_guess
    p_s = state.p_slip
    p_t = state.p_transit

    if is_correct:
        p_correct_given_l = 1 - p_s
        p_correct_given_not_l = p_g
        p_l_given_correct = (p_l * p_correct_given_l) / (
            p_l * p_correct_given_l + (1 - p_l) * p_correct_given_not_l
        )
        p_l_new = p_l_given_correct + (1 - p_l_given_correct) * p_t
    else:
        p_wrong_given_l = p_s
        p_wrong_given_not_l = 1 - p_g
        p_l_given_wrong = (p_l * p_wrong_given_l) / (
            p_l * p_wrong_given_l + (1 - p_l) * p_wrong_given_not_l
        )
        p_l_new = p_l_given_wrong + (1 - p_l_given_wrong) * p_t

    p_l_new = max(0.01, min(0.99, p_l_new))

    state.p_mastery = p_l_new
    state.attempt_count += 1
    if is_correct:
        state.correct_count += 1
    state.save()

    cache.set(_cache_key(student_id, concept_id), state, CACHE_TTL)

    logger.debug(
        "BKT update: student=%s, concept=%s, correct=%s, P(L): %.3f -> %.3f",
        student_id, concept_id, is_correct, p_l, p_l_new,
    )
    return state


def decide_pathway_action(student_id: int, concept_id: int) -> dict:
    t0 = time.monotonic()

    state = get_mastery_state(student_id, concept_id)
    p = state.p_mastery

    if p < THRESHOLDS["MASTERY_LOW"]:
        content = _find_supplementary(concept_id, difficulty_max=1)
        intervention = _log_intervention(
            student_id, concept_id,
            ContentIntervention.InterventionType.SUPPLEMENTARY,
            "bkt_low_mastery", p, content,
        )
        emit_event(
            EventLog.EventName.CONTENT_INTERVENTION,
            actor_type=EventLog.ActorType.SYSTEM,
            concept=concept_id,
            mastery_before=p,
            mastery_after=p,
            intervention_reason="bkt_low_mastery",
            properties={
                "intervention_id": intervention.id,
                "intervention_type": "supplementary",
            },
            confirmed=True,
        )
        result = {
            "action": "supplement",
            "difficulty_adjustment": -1,
            "p_mastery": p,
            "supplementary_content": content,
            "message": "Bạn cần ôn lại khái niệm này. Hãy xem tài liệu bổ trợ.",
        }
        decision_type = "supplement"

    elif p > THRESHOLDS["MASTERY_HIGH"]:
        next_concept = _find_next_concept(concept_id)
        _log_intervention(
            student_id, concept_id,
            ContentIntervention.InterventionType.DIFFICULTY_UP,
            "bkt_high_mastery", p,
        )
        result = {
            "action": "advance",
            "difficulty_adjustment": 1,
            "p_mastery": p,
            "next_concept_id": next_concept.id if next_concept else None,
            "message": "Tuyệt vời! Bạn đã nắm vững. Tiếp tục với nội dung nâng cao.",
        }
        decision_type = "advance"

    else:
        result = {
            "action": "continue",
            "difficulty_adjustment": 0,
            "p_mastery": p,
            "message": "Tiếp tục luyện tập để củng cố kiến thức.",
        }
        decision_type = "continue"

    duration = time.monotonic() - t0
    ADAPTIVE_DECISION_DURATION.labels(decision_type=decision_type).observe(duration)

    return result


def _find_supplementary(concept_id: int, difficulty_max: int = 1):
    return (
        SupplementaryContent.objects
        .filter(concept_id=concept_id, difficulty_target__lte=difficulty_max)
        .order_by("order")
        .values("id", "title", "content_type", "body", "media_url")
        .first()
    )


def _find_next_concept(concept_id: int):
    try:
        current = Concept.objects.get(id=concept_id)
        return (
            Concept.objects
            .filter(course=current.course, order__gt=current.order, is_active=True)
            .order_by("order")
            .first()
        )
    except Concept.DoesNotExist:
        return None


def _log_intervention(student_id, concept_id, itype, rule, p_mastery, content=None):
    return ContentIntervention.objects.create(
        student_id=student_id,
        concept_id=concept_id,
        intervention_type=itype,
        source_rule=rule,
        p_mastery_at_trigger=p_mastery,
        content_id=content["id"] if content else None,
    )
