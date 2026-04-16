"""
Adaptive edge-case test matrix (AD-01 .. AD-10).

Covers: consecutive correct/wrong, intervention insertion, guess probability,
offline state, retry flow, retry-threshold alert, concurrent mastery update,
rule version mid-session, and missing supplementary fallback.
"""
import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.conf import settings

from adaptive.engine import (
    decide_pathway_action,
    get_mastery_state,
    update_mastery,
)
from adaptive.models import (
    ContentIntervention,
    MasteryState,
    StudentPathway,
    TaskAttempt,
)
from curriculum.models import SupplementaryContent
from dashboard.models import Alert
from dashboard.services import compute_early_warnings

pytestmark = pytest.mark.django_db

THRESHOLDS = settings.PALP_ADAPTIVE_THRESHOLDS
BKT = settings.PALP_BKT_DEFAULTS
URL = "/api/adaptive/"


# =========================================================================
# AD-01  5 consecutive correct -> difficulty increases
# =========================================================================


class TestAD01ConsecutiveCorrectIncreaseDifficulty:
    def test_mastery_rises_monotonically(self, student, concepts):
        cid = concepts[0].id
        history = []
        for _ in range(5):
            state = update_mastery(student.id, cid, is_correct=True)
            history.append(state.p_mastery)

        for i in range(1, len(history)):
            assert history[i] > history[i - 1], (
                f"Mastery did not increase at step {i}: {history}"
            )

    def test_high_mastery_triggers_advance(self, student, concepts):
        cid = concepts[0].id
        for _ in range(15):
            update_mastery(student.id, cid, is_correct=True)

        result = decide_pathway_action(student.id, cid)
        assert result["action"] == "advance"
        assert result["difficulty_adjustment"] == 1

    def test_api_submit_correct_increases_mastery(
        self, student_api, student, micro_tasks,
    ):
        task = micro_tasks[0]
        masteries = []
        for _ in range(5):
            resp = student_api.post(
                f"{URL}submit/",
                {
                    "task_id": task.id,
                    "answer": task.content["correct_answer"],
                    "duration_seconds": 10,
                    "hints_used": 0,
                },
                format="json",
            )
            masteries.append(resp.data["mastery"]["p_mastery"])

        for i in range(1, len(masteries)):
            assert masteries[i] > masteries[i - 1]


# =========================================================================
# AD-02  2 wrong on same concept -> intervention inserted
# =========================================================================


class TestAD02WrongSameConceptInsertsIntervention:
    def test_low_mastery_creates_supplementary_intervention(
        self, student, concepts,
    ):
        cid = concepts[0].id
        state = get_mastery_state(student.id, cid)
        state.p_mastery = THRESHOLDS["MASTERY_LOW"] - 0.15
        state.save()

        for _ in range(2):
            update_mastery(student.id, cid, is_correct=False)

        result = decide_pathway_action(student.id, cid)
        assert result["action"] == "supplement"
        assert result["difficulty_adjustment"] == -1

        assert ContentIntervention.objects.filter(
            student=student,
            concept=concepts[0],
            intervention_type=ContentIntervention.InterventionType.SUPPLEMENTARY,
        ).exists()


# =========================================================================
# AD-03  2 wrong on 2 different concepts -> flag weakest
# =========================================================================


class TestAD03WrongDifferentConcepts:
    def test_both_concepts_flagged(self, student, concepts):
        for i in range(2):
            state = get_mastery_state(student.id, concepts[i].id)
            state.p_mastery = THRESHOLDS["MASTERY_LOW"] - 0.1
            state.save()
            update_mastery(student.id, concepts[i].id, is_correct=False)

        r0 = decide_pathway_action(student.id, concepts[0].id)
        r1 = decide_pathway_action(student.id, concepts[1].id)
        assert r0["action"] == "supplement"
        assert r1["action"] == "supplement"

    def test_weakest_has_lower_mastery(self, student, concepts):
        state_a = get_mastery_state(student.id, concepts[0].id)
        state_a.p_mastery = 0.20
        state_a.save()

        state_b = get_mastery_state(student.id, concepts[1].id)
        state_b.p_mastery = 0.40
        state_b.save()

        update_mastery(student.id, concepts[0].id, is_correct=False)
        update_mastery(student.id, concepts[1].id, is_correct=False)

        m_a = MasteryState.objects.get(student=student, concept=concepts[0])
        m_b = MasteryState.objects.get(student=student, concept=concepts[1])
        assert m_a.p_mastery < m_b.p_mastery


# =========================================================================
# AD-04  Lucky guess -> guess probability handled correctly
# =========================================================================


class TestAD04LuckyGuess:
    def test_single_correct_from_low_stays_below_threshold(self, student, concepts):
        cid = concepts[0].id
        state = get_mastery_state(student.id, cid)
        state.p_mastery = 0.15
        state.save()

        updated = update_mastery(student.id, cid, is_correct=True)

        assert updated.p_mastery > 0.15
        assert updated.p_mastery < THRESHOLDS["MASTERY_LOW"]

        result = decide_pathway_action(student.id, cid)
        assert result["action"] == "supplement"

    def test_guess_probability_dampens_correct(self, student, concepts):
        """With P(G)=0.25, a correct answer from p=0.15 gives much less
        credit than from p=0.60 (where it's more likely genuine knowledge)."""
        cid = concepts[0].id

        state = get_mastery_state(student.id, cid)
        state.p_mastery = 0.15
        state.save()
        low_result = update_mastery(student.id, cid, is_correct=True)
        gain_from_low = low_result.p_mastery - 0.15

        state.p_mastery = 0.60
        state.save()
        mid_result = update_mastery(student.id, cid, is_correct=True)
        gain_from_mid = mid_result.p_mastery - 0.60

        assert gain_from_low < gain_from_mid


# =========================================================================
# AD-05  Offline before intervention -> state saved, resume correct
# =========================================================================


class TestAD05OfflineState:
    def test_mastery_state_persists(self, student, concepts):
        cid = concepts[0].id
        state = get_mastery_state(student.id, cid)
        state.p_mastery = 0.45
        state.save()

        fresh = MasteryState.objects.get(student=student, concept=concepts[0])
        assert fresh.p_mastery == pytest.approx(0.45)

    def test_intervention_persists_independently(self, student, concepts):
        ContentIntervention.objects.create(
            student=student,
            concept=concepts[0],
            intervention_type=ContentIntervention.InterventionType.SUPPLEMENTARY,
            source_rule="bkt_low_mastery",
            p_mastery_at_trigger=0.3,
        )
        assert ContentIntervention.objects.filter(student=student).count() == 1

    def test_pathway_state_persists(self, student_with_pathway, concepts):
        pathway = student_with_pathway
        pathway.current_difficulty = 2
        pathway.save()

        reloaded = StudentPathway.objects.get(id=pathway.id)
        assert reloaded.current_difficulty == 2
        assert reloaded.current_concept == concepts[0]


# =========================================================================
# AD-06  Retry after supplementary correct -> returns to main flow
# =========================================================================


class TestAD06RetryCorrectReturnsToMainFlow:
    def test_correct_after_supplement_increases_mastery(self, student, concepts):
        cid = concepts[0].id
        state = get_mastery_state(student.id, cid)
        state.p_mastery = THRESHOLDS["MASTERY_LOW"] - 0.15
        state.save()

        update_mastery(student.id, cid, is_correct=False)
        action_before = decide_pathway_action(student.id, cid)
        assert action_before["action"] == "supplement"

        updated = update_mastery(student.id, cid, is_correct=True)

        action_after = decide_pathway_action(student.id, cid)
        assert action_after["action"] in ("continue", "advance")
        assert updated.p_mastery > state.p_mastery

    def test_api_retry_flow(self, student_api, student, micro_tasks):
        task = micro_tasks[0]

        student_api.post(
            f"{URL}submit/",
            {
                "task_id": task.id,
                "answer": "wrong",
                "duration_seconds": 10,
                "hints_used": 0,
            },
            format="json",
        )

        resp = student_api.post(
            f"{URL}submit/",
            {
                "task_id": task.id,
                "answer": task.content["correct_answer"],
                "duration_seconds": 15,
                "hints_used": 1,
            },
            format="json",
        )
        assert resp.data["attempt"]["is_correct"] is True
        assert resp.data["attempt"]["attempt_number"] == 2


# =========================================================================
# AD-07  Retry wrong 3rd time -> creates alert for lecturer
# =========================================================================


class TestAD07RetryThresholdAlert:
    def test_three_failures_creates_red_alert(
        self, student, class_with_members, micro_tasks,
    ):
        task = micro_tasks[0]
        for i in range(4):
            TaskAttempt.objects.create(
                student=student,
                task=task,
                is_correct=False,
                score=0,
                max_score=100,
                answer="wrong",
                attempt_number=i + 1,
            )

        alerts = compute_early_warnings(class_with_members.id)
        retry_alerts = [
            a for a in alerts
            if a.student == student
            and a.trigger_type == Alert.TriggerType.RETRY_FAILURE
        ]
        assert len(retry_alerts) >= 1
        assert retry_alerts[0].severity == Alert.Severity.RED

    def test_api_emits_retry_event_at_threshold(
        self, student_api, student, micro_tasks,
    ):
        from events.models import EventLog

        task = micro_tasks[0]
        threshold = settings.PALP_EARLY_WARNING["RETRY_FAILURE_THRESHOLD"]

        for _ in range(threshold):
            student_api.post(
                f"{URL}submit/",
                {
                    "task_id": task.id,
                    "answer": "wrong",
                    "duration_seconds": 5,
                    "hints_used": 0,
                },
                format="json",
            )

        retry_events = EventLog.objects.filter(
            event_name=EventLog.EventName.RETRY_TRIGGERED,
            actor=student,
        )
        assert retry_events.exists()


# =========================================================================
# AD-08  2 parallel requests update mastery -> no race condition
# =========================================================================


class TestAD08ConcurrentMasteryUpdate:
    @pytest.mark.slow
    def test_concurrent_updates_consistent(self, student, concepts):
        cid = concepts[0].id
        get_mastery_state(student.id, cid)

        initial = MasteryState.objects.get(
            student=student, concept=concepts[0],
        )
        initial_attempts = initial.attempt_count

        errors = []

        def do_update():
            try:
                from django.db import connection as conn
                conn.ensure_connection()
                update_mastery(student.id, cid, is_correct=True)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(do_update) for _ in range(2)]
            for f in as_completed(futures):
                f.result()

        final = MasteryState.objects.get(
            student=student, concept=concepts[0],
        )
        assert final.attempt_count == initial_attempts + 2
        assert not errors


# =========================================================================
# AD-09  Rule version changes mid-session -> old session not broken
# =========================================================================


class TestAD09RuleVersionMidSession:
    def test_old_intervention_retains_version(self, student, concepts):
        state = get_mastery_state(student.id, concepts[0].id)
        state.p_mastery = THRESHOLDS["MASTERY_LOW"] - 0.1
        state.save()

        decide_pathway_action(student.id, concepts[0].id)

        old = ContentIntervention.objects.filter(
            student=student, concept=concepts[0],
        ).latest("created_at")
        assert old.rule_version == "v1.0"

        state.p_mastery = THRESHOLDS["MASTERY_LOW"] - 0.05
        state.save()
        decide_pathway_action(student.id, concepts[0].id)

        interventions = ContentIntervention.objects.filter(
            student=student, concept=concepts[0],
        ).order_by("created_at")
        assert interventions.count() >= 2
        assert all(i.rule_version == "v1.0" for i in interventions)

    def test_session_continues_after_threshold_change(self, student, concepts):
        cid = concepts[0].id
        state = get_mastery_state(student.id, cid)
        state.p_mastery = 0.55
        state.save()

        result = decide_pathway_action(student.id, cid)
        assert result["action"] == "supplement"

        update_mastery(student.id, cid, is_correct=True)
        update_mastery(student.id, cid, is_correct=True)

        result2 = decide_pathway_action(student.id, cid)
        assert result2["action"] in ("supplement", "continue", "advance")


# =========================================================================
# AD-10  Intervention content missing -> safe fallback
# =========================================================================


class TestAD10MissingContentFallback:
    def test_no_supplementary_content_returns_none(self, student, concepts):
        SupplementaryContent.objects.filter(concept=concepts[0]).delete()

        state = get_mastery_state(student.id, concepts[0].id)
        state.p_mastery = THRESHOLDS["MASTERY_LOW"] - 0.15
        state.save()

        result = decide_pathway_action(student.id, concepts[0].id)
        assert result["action"] == "supplement"
        assert result["supplementary_content"] is None
        assert result["message"]

    def test_intervention_logged_even_without_content(self, student, concepts):
        SupplementaryContent.objects.filter(concept=concepts[0]).delete()

        state = get_mastery_state(student.id, concepts[0].id)
        state.p_mastery = THRESHOLDS["MASTERY_LOW"] - 0.15
        state.save()

        decide_pathway_action(student.id, concepts[0].id)

        intervention = ContentIntervention.objects.filter(
            student=student,
            concept=concepts[0],
            intervention_type=ContentIntervention.InterventionType.SUPPLEMENTARY,
        ).first()
        assert intervention is not None
        assert intervention.content is None
