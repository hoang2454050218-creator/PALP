"""
Learning Integrity Tests -- 6 Failure Condition Verification (LI-F01..LI-F06).

QA_STANDARD Section 1.5.2.

"Many systems are technically correct but pedagogically wrong."
These tests verify that PALP's adaptive engine makes educationally
sound decisions, not just mathematically correct ones.
"""
import pytest
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from accounts.models import User
from adaptive.engine import update_mastery, decide_pathway_action, get_mastery_state
from adaptive.models import MasteryState, TaskAttempt, ContentIntervention, StudentPathway
from curriculum.models import SupplementaryContent
from dashboard.models import Alert
from dashboard.services import compute_early_warnings
from events.models import EventLog

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.integration]

THRESHOLDS = settings.PALP_ADAPTIVE_THRESHOLDS


# ---------------------------------------------------------------------------
# LI-F01: Wrong concept supplementary content
# ---------------------------------------------------------------------------


class TestLIF01WrongConceptIntervention:
    """
    Supplementary content must relate to the EXACT concept the student
    is struggling with. Serving content for concept A when the student
    is weak on concept B is a pedagogical error.
    """

    def test_supplement_matches_weak_concept(self, student, concepts):
        weak_concept = concepts[0]
        strong_concept = concepts[1] if len(concepts) > 1 else concepts[0]

        SupplementaryContent.objects.create(
            concept=weak_concept,
            title="Bo tro concept 0",
            content_type=SupplementaryContent.ContentType.TEXT,
            body="Noi dung bo tro",
            difficulty_target=1,
            order=1,
        )

        state = get_mastery_state(student.id, weak_concept.id)
        state.p_mastery = THRESHOLDS["MASTERY_LOW"] - 0.15
        state.save()

        result = decide_pathway_action(student.id, weak_concept.id)
        assert result["action"] == "supplement"

        if result.get("supplementary_content"):
            intervention = ContentIntervention.objects.filter(
                student=student,
            ).latest("created_at")
            assert intervention.concept_id == weak_concept.id, (
                f"Intervention concept {intervention.concept_id} != "
                f"weak concept {weak_concept.id}"
            )

    def test_intervention_logged_for_correct_concept(self, student, concepts):
        concept = concepts[0]
        state = get_mastery_state(student.id, concept.id)
        state.p_mastery = THRESHOLDS["MASTERY_LOW"] - 0.1
        state.save()

        decide_pathway_action(student.id, concept.id)

        interventions = ContentIntervention.objects.filter(student=student)
        for intervention in interventions:
            assert intervention.concept_id == concept.id

    def test_no_cross_concept_contamination(self, student, concepts):
        if len(concepts) < 2:
            pytest.skip("Need >= 2 concepts")

        concept_a, concept_b = concepts[0], concepts[1]

        state_a = get_mastery_state(student.id, concept_a.id)
        state_a.p_mastery = 0.90
        state_a.save()

        state_b = get_mastery_state(student.id, concept_b.id)
        state_b.p_mastery = 0.30
        state_b.save()

        result = decide_pathway_action(student.id, concept_b.id)
        if result["action"] == "supplement":
            interventions = ContentIntervention.objects.filter(
                student=student,
                concept=concept_a,
                intervention_type=ContentIntervention.InterventionType.SUPPLEMENTARY,
            )
            assert interventions.count() == 0, (
                "Should not create supplementary intervention for strong concept A "
                "when student is weak on concept B"
            )


# ---------------------------------------------------------------------------
# LI-F02: Premature difficulty increase
# ---------------------------------------------------------------------------


class TestLIF02PrematureDifficultyIncrease:
    """
    Must NOT advance or increase difficulty when mastery is below threshold.
    Must NOT oscillate difficulty abnormally.
    """

    def test_no_advance_below_high_threshold(self, student, concepts):
        state = get_mastery_state(student.id, concepts[0].id)
        state.p_mastery = THRESHOLDS["MASTERY_HIGH"] - 0.05
        state.save()

        result = decide_pathway_action(student.id, concepts[0].id)
        assert result["action"] != "advance", (
            f"Should not advance when mastery "
            f"({state.p_mastery}) < MASTERY_HIGH ({THRESHOLDS['MASTERY_HIGH']})"
        )
        assert result["difficulty_adjustment"] <= 0

    def test_no_advance_at_exact_low_threshold(self, student, concepts):
        state = get_mastery_state(student.id, concepts[0].id)
        state.p_mastery = THRESHOLDS["MASTERY_LOW"]
        state.save()

        result = decide_pathway_action(student.id, concepts[0].id)
        assert result["action"] != "advance"
        assert result["difficulty_adjustment"] <= 0

    def test_advance_only_above_high_threshold(self, student, concepts):
        state = get_mastery_state(student.id, concepts[0].id)
        state.p_mastery = THRESHOLDS["MASTERY_HIGH"] + 0.05
        state.attempt_count = THRESHOLDS.get("MIN_ATTEMPTS_FOR_ADVANCE", 3) + 1
        state.save()

        result = decide_pathway_action(student.id, concepts[0].id)
        assert result["action"] == "advance"
        assert result["difficulty_adjustment"] == 1

    def test_difficulty_does_not_oscillate(self, student, concepts):
        concept_id = concepts[0].id
        actions = []

        pattern = [True, False, True, False, True, False, True, True, True, True]
        for is_correct in pattern:
            update_mastery(student.id, concept_id, is_correct=is_correct)
            result = decide_pathway_action(student.id, concept_id)
            actions.append(result["difficulty_adjustment"])

        oscillations = 0
        for i in range(2, len(actions)):
            if (actions[i] > 0 and actions[i - 1] < 0) or \
               (actions[i] < 0 and actions[i - 1] > 0):
                oscillations += 1

        assert oscillations <= 2, (
            f"Difficulty oscillated {oscillations} times in 10 steps: {actions}"
        )


# ---------------------------------------------------------------------------
# LI-F03: Mass false flagging
# ---------------------------------------------------------------------------


class TestLIF03MassFalseFlagging:
    """
    If >= 3 normal students are incorrectly flagged RED/YELLOW in the same
    batch, it indicates a systematic bug in early warning logic.
    """

    def test_active_students_not_mass_flagged(self, class_with_members):
        now = timezone.now()
        students = User.objects.filter(
            class_memberships__student_class=class_with_members,
            role=User.Role.STUDENT,
        )

        for student in students:
            EventLog.objects.create(
                event_name=EventLog.EventName.SESSION_STARTED,
                timestamp_utc=now - timedelta(hours=2),
                actor=student,
                actor_type=EventLog.ActorType.STUDENT,
            )

        alerts = compute_early_warnings(class_with_members.id)
        false_flags = [
            a for a in alerts
            if a.severity in (Alert.Severity.RED, Alert.Severity.YELLOW)
            and a.trigger_type == Alert.TriggerType.INACTIVITY
        ]

        assert len(false_flags) == 0, (
            f"Active students falsely flagged: {len(false_flags)} alerts created "
            f"for students who were active 2 hours ago"
        )

    def test_no_duplicate_alerts_for_same_student(self, student, class_with_members):
        EventLog.objects.create(
            event_name=EventLog.EventName.SESSION_STARTED,
            timestamp_utc=timezone.now() - timedelta(days=6),
            actor=student,
            actor_type=EventLog.ActorType.STUDENT,
        )

        compute_early_warnings(class_with_members.id)
        first_count = Alert.objects.filter(student=student).count()

        compute_early_warnings(class_with_members.id)
        second_count = Alert.objects.filter(student=student).count()

        assert first_count == second_count, (
            "Running early warning twice should not create duplicate alerts"
        )


# ---------------------------------------------------------------------------
# LI-F04: No return to main flow after recovery
# ---------------------------------------------------------------------------


class TestLIF04NoReturnToMainFlow:
    """
    After a student recovers (mastery rises above 0.60 after being in
    supplement), the system must route them back to the main learning path.
    """

    def test_student_returns_to_continue_after_recovery(self, student, concepts):
        concept_id = concepts[0].id

        state = get_mastery_state(student.id, concept_id)
        state.p_mastery = 0.40
        state.save()
        result_before = decide_pathway_action(student.id, concept_id)
        assert result_before["action"] == "supplement"

        for _ in range(15):
            state = update_mastery(student.id, concept_id, is_correct=True)

        assert state.p_mastery > THRESHOLDS["MASTERY_LOW"]
        result_after = decide_pathway_action(student.id, concept_id)
        assert result_after["action"] in ("continue", "advance"), (
            f"Student recovered to {state.p_mastery:.2f} but still stuck "
            f"in '{result_after['action']}' instead of continue/advance"
        )

    def test_recovered_student_not_stuck_in_supplement_loop(self, student, concepts):
        concept_id = concepts[0].id

        state = get_mastery_state(student.id, concept_id)
        state.p_mastery = 0.75
        state.save()

        for _ in range(5):
            result = decide_pathway_action(student.id, concept_id)
            assert result["action"] != "supplement", (
                f"Mastery is {state.p_mastery:.2f} (above threshold) "
                f"but action is still 'supplement'"
            )


# ---------------------------------------------------------------------------
# LI-F05: Inflated progress display
# ---------------------------------------------------------------------------


class TestLIF05InflatedProgress:
    """
    Progress percentage and mastery display must not be inflated by
    double-counting or calculation errors.
    """

    def test_attempt_count_matches_actual_attempts(
        self, student, student_api, micro_tasks, student_with_pathway,
    ):
        task = micro_tasks[0]
        n_attempts = 3

        for i in range(n_attempts):
            student_api.post("/api/adaptive/submit/", {
                "task_id": task.pk,
                "answer": task.content.get("correct_answer", "A") if i == 2 else "WRONG",
                "duration_seconds": 30,
                "hints_used": 0,
            }, format="json")

        actual_count = TaskAttempt.objects.filter(
            student=student, task=task,
        ).count()
        assert actual_count == n_attempts

        ms = MasteryState.objects.get(student=student, concept=task.concept)
        assert ms.attempt_count == n_attempts
        assert ms.correct_count == 1

    def test_mastery_reflects_actual_performance(self, student, concepts):
        concept_id = concepts[0].id

        for _ in range(5):
            update_mastery(student.id, concept_id, is_correct=True)
        for _ in range(5):
            update_mastery(student.id, concept_id, is_correct=False)

        state = MasteryState.objects.get(student_id=student.id, concept_id=concept_id)

        assert state.attempt_count == 10
        assert state.correct_count == 5
        assert state.p_mastery < 0.85, (
            f"50% correct rate but mastery is {state.p_mastery:.2f} "
            f"(should not be >= 0.85)"
        )


# ---------------------------------------------------------------------------
# LI-F06: Alert without specific reason
# ---------------------------------------------------------------------------


class TestLIF06AlertWithoutReason:
    """
    Every alert must have a human-readable reason that explains WHY
    the student was flagged — not an error code or empty string.
    """

    def test_generated_alerts_have_nonempty_reason(self, student, class_with_members):
        EventLog.objects.create(
            event_name=EventLog.EventName.SESSION_STARTED,
            timestamp_utc=timezone.now() - timedelta(days=6),
            actor=student,
            actor_type=EventLog.ActorType.STUDENT,
        )

        alerts = compute_early_warnings(class_with_members.id)

        for alert in alerts:
            assert alert.reason is not None
            assert alert.reason.strip() != ""
            assert len(alert.reason) >= 10, (
                f"Alert reason too short: '{alert.reason}'"
            )

    def test_alert_reason_is_not_error_code(self, student, class_with_members):
        EventLog.objects.create(
            event_name=EventLog.EventName.SESSION_STARTED,
            timestamp_utc=timezone.now() - timedelta(days=6),
            actor=student,
            actor_type=EventLog.ActorType.STUDENT,
        )

        alerts = compute_early_warnings(class_with_members.id)

        for alert in alerts:
            assert not alert.reason.startswith("ERR_")
            assert not alert.reason.startswith("{")
            assert not alert.reason.startswith("[")
            assert "traceback" not in alert.reason.lower()
            assert "exception" not in alert.reason.lower()

    def test_alert_has_evidence_and_suggested_action(self, student, class_with_members):
        EventLog.objects.create(
            event_name=EventLog.EventName.SESSION_STARTED,
            timestamp_utc=timezone.now() - timedelta(days=6),
            actor=student,
            actor_type=EventLog.ActorType.STUDENT,
        )

        alerts = compute_early_warnings(class_with_members.id)

        for alert in alerts:
            assert alert.evidence is not None
            assert isinstance(alert.evidence, dict)
            assert len(alert.evidence) > 0
            assert alert.suggested_action is not None
            assert alert.suggested_action.strip() != ""

    def test_alert_reason_mentions_student_context(self, student, class_with_members):
        EventLog.objects.create(
            event_name=EventLog.EventName.SESSION_STARTED,
            timestamp_utc=timezone.now() - timedelta(days=6),
            actor=student,
            actor_type=EventLog.ActorType.STUDENT,
        )

        alerts = compute_early_warnings(class_with_members.id)

        for alert in alerts:
            reason_lower = alert.reason.lower()
            has_context = any(word in reason_lower for word in [
                "sinh viên", "ngày", "lần", "concept", "mastery",
                "không hoạt động", "thất bại", "tiến độ",
            ])
            assert has_context, (
                f"Alert reason lacks student context: '{alert.reason}'"
            )


# ---------------------------------------------------------------------------
# LI Cross-cutting: Psychological safety in labels
# ---------------------------------------------------------------------------


class TestLIPsychologicalSafety:
    """
    System messages and labels must never use judgmental or harmful
    wording about student ability.
    """

    FORBIDDEN_WORDS = ["yếu", "kém", "dốt", "lười", "thất bại", "tệ", "ngu"]

    def test_alert_reason_no_judgmental_words(self, student, class_with_members):
        EventLog.objects.create(
            event_name=EventLog.EventName.SESSION_STARTED,
            timestamp_utc=timezone.now() - timedelta(days=6),
            actor=student,
            actor_type=EventLog.ActorType.STUDENT,
        )

        alerts = compute_early_warnings(class_with_members.id)

        for alert in alerts:
            for word in self.FORBIDDEN_WORDS:
                assert word not in alert.reason.lower(), (
                    f"Alert reason contains judgmental word '{word}': "
                    f"'{alert.reason}'"
                )

    def test_suggested_action_no_judgmental_words(self, student, class_with_members):
        EventLog.objects.create(
            event_name=EventLog.EventName.SESSION_STARTED,
            timestamp_utc=timezone.now() - timedelta(days=6),
            actor=student,
            actor_type=EventLog.ActorType.STUDENT,
        )

        alerts = compute_early_warnings(class_with_members.id)

        for alert in alerts:
            for word in self.FORBIDDEN_WORDS:
                assert word not in alert.suggested_action.lower(), (
                    f"Suggested action contains judgmental word '{word}': "
                    f"'{alert.suggested_action}'"
                )
