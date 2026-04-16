import logging
from collections import defaultdict
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from events.services import audit_log
from events.models import EventLog
from .models import AssessmentSession, AssessmentResponse, AssessmentQuestion, LearnerProfile

logger = logging.getLogger("palp")


def evaluate_answer(question: AssessmentQuestion, answer) -> bool:
    correct = question.correct_answer
    if question.question_type == AssessmentQuestion.QuestionType.MULTIPLE_CHOICE:
        return str(answer) == str(correct)
    if question.question_type == AssessmentQuestion.QuestionType.TRUE_FALSE:
        return str(answer).lower() == str(correct).lower()
    if question.question_type == AssessmentQuestion.QuestionType.DRAG_DROP:
        if isinstance(correct, list) and isinstance(answer, list):
            return answer == correct
    return str(answer) == str(correct)


def check_session_timeout(session: AssessmentSession) -> None:
    if session.status != AssessmentSession.Status.IN_PROGRESS:
        return
    if session.is_expired:
        session.status = AssessmentSession.Status.EXPIRED
        session.save(update_fields=["status"])
        audit_log(
            session.student,
            EventLog.EventName.ASSESS_EXPIRED,
            {"session_id": session.id, "assessment_id": session.assessment_id},
        )
        raise ValidationError(
            {"detail": "Đã hết thời gian làm bài.", "code": "session_expired"}
        )


def submit_answer(
    session: AssessmentSession,
    question_id: int,
    answer,
    time_taken: int,
    client_version: int | None = None,
) -> AssessmentResponse:
    check_session_timeout(session)

    if session.status != AssessmentSession.Status.IN_PROGRESS:
        raise ValidationError(
            {"detail": "Phiên làm bài không còn hoạt động.", "code": "session_not_active"}
        )

    with transaction.atomic():
        locked_session = (
            AssessmentSession.objects
            .select_for_update()
            .get(id=session.id)
        )

        if client_version is not None and locked_session.version != client_version:
            raise ValidationError(
                {"detail": "Phiên bị xung đột từ tab khác.", "code": "version_conflict"}
            )

        question = AssessmentQuestion.objects.get(id=question_id, assessment=locked_session.assessment)
        is_correct = evaluate_answer(question, answer)

        response, _ = AssessmentResponse.objects.update_or_create(
            session=locked_session,
            question=question,
            defaults={
                "answer": answer,
                "is_correct": is_correct,
                "time_taken_seconds": time_taken,
            },
        )

        locked_session.version += 1
        locked_session.save(update_fields=["version"])

    audit_log(
        session.student,
        EventLog.EventName.ASSESS_ANSWER,
        {
            "session_id": session.id,
            "question_id": question_id,
            "is_correct": is_correct,
        },
    )
    return response


def complete_assessment(session_id: int, student_id: int) -> LearnerProfile:
    with transaction.atomic():
        session = (
            AssessmentSession.objects
            .select_for_update()
            .select_related("assessment")
            .get(id=session_id, student_id=student_id)
        )

        if session.status == AssessmentSession.Status.COMPLETED:
            return LearnerProfile.objects.get(
                student_id=student_id,
                course=session.assessment.course,
            )

        if session.status != AssessmentSession.Status.IN_PROGRESS:
            raise ValidationError(
                {"detail": "Phiên không hợp lệ để nộp bài.", "code": "invalid_session_state"}
            )

        if session.is_expired:
            session.status = AssessmentSession.Status.EXPIRED
            session.save(update_fields=["status"])
            raise ValidationError(
                {"detail": "Đã hết thời gian làm bài.", "code": "session_expired"}
            )

        now = timezone.now()
        session.status = AssessmentSession.Status.COMPLETED
        session.completed_at = now
        session.submitted_at = now

        responses = session.responses.select_related("question__concept").all()
        total_points = 0
        earned_points = 0
        concept_scores = defaultdict(lambda: {"correct": 0, "total": 0})
        total_time = 0

        for resp in responses:
            total_points += resp.question.points
            total_time += resp.time_taken_seconds
            concept_id = str(resp.question.concept_id)
            concept_scores[concept_id]["total"] += 1
            if resp.is_correct:
                earned_points += resp.question.points
                concept_scores[concept_id]["correct"] += 1

        score_pct = (earned_points / total_points * 100) if total_points > 0 else 0
        session.total_score = score_pct
        session.total_time_seconds = total_time
        session.save()

        initial_mastery = {}
        strengths = []
        weaknesses = []
        for concept_id, data in concept_scores.items():
            mastery = data["correct"] / data["total"] if data["total"] > 0 else 0
            initial_mastery[concept_id] = round(mastery, 2)
            if mastery >= 0.7:
                strengths.append(int(concept_id))
            elif mastery < 0.5:
                weaknesses.append(int(concept_id))

        recommended = None
        if weaknesses:
            from curriculum.models import Concept
            recommended = Concept.objects.filter(id__in=weaknesses).order_by("order").first()

        profile, _ = LearnerProfile.objects.update_or_create(
            student_id=student_id,
            course=session.assessment.course,
            defaults={
                "assessment_session": session,
                "overall_score": score_pct,
                "initial_mastery": initial_mastery,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "recommended_start_concept": recommended,
            },
        )

    _seed_mastery_from_assessment(student_id, session.assessment.course, initial_mastery)
    _initialize_pathway(student_id, session.assessment.course, recommended)

    audit_log(
        session.student,
        EventLog.EventName.ASSESS_COMPLETE,
        {
            "session_id": session.id,
            "score": round(score_pct, 2),
            "total_time_seconds": total_time,
            "question_count": len(responses),
        },
    )
    logger.info(f"Assessment completed for user={student_id}: score={score_pct:.1f}%")
    return profile


def _seed_mastery_from_assessment(student_id, course, initial_mastery: dict):
    from django.conf import settings as _settings
    from adaptive.models import MasteryState

    bkt = _settings.PALP_BKT_DEFAULTS
    for concept_id_str, mastery_score in initial_mastery.items():
        concept_id = int(concept_id_str)
        state, created = MasteryState.objects.get_or_create(
            student_id=student_id,
            concept_id=concept_id,
            defaults={
                "p_mastery": mastery_score,
                "p_guess": bkt["P_GUESS"],
                "p_slip": bkt["P_SLIP"],
                "p_transit": bkt["P_TRANSIT"],
            },
        )
        if not created and state.attempt_count == 0:
            state.p_mastery = mastery_score
            state.save(update_fields=["p_mastery"])


def _initialize_pathway(student_id, course, recommended_concept):
    from adaptive.models import StudentPathway
    from curriculum.models import Concept, Milestone

    if recommended_concept is None:
        recommended_concept = (
            Concept.objects.filter(course=course, is_active=True)
            .order_by("order")
            .first()
        )

    first_milestone = None
    if recommended_concept:
        first_milestone = (
            recommended_concept.milestones.filter(is_active=True)
            .order_by("order")
            .first()
        )
    if first_milestone is None:
        first_milestone = (
            Milestone.objects.filter(course=course, is_active=True)
            .order_by("order")
            .first()
        )

    StudentPathway.objects.update_or_create(
        student_id=student_id,
        course=course,
        defaults={
            "current_concept": recommended_concept,
            "current_milestone": first_milestone,
        },
    )
