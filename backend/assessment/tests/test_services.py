import pytest

from assessment.models import (
    Assessment,
    AssessmentQuestion,
    AssessmentResponse,
    AssessmentSession,
    LearnerProfile,
)
from assessment.services import evaluate_answer, submit_answer, complete_assessment
from adaptive.models import MasteryState, StudentPathway

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# evaluate_answer
# ---------------------------------------------------------------------------


class TestEvaluateAnswer:
    def test_correct_multiple_choice(self, assessment):
        q = assessment.questions.first()
        assert evaluate_answer(q, "A") is True

    def test_wrong_multiple_choice(self, assessment):
        q = assessment.questions.first()
        assert evaluate_answer(q, "B") is False

    def test_true_false(self, course, concepts):
        a = Assessment.objects.create(course=course, title="TF Assessment")
        q = AssessmentQuestion.objects.create(
            assessment=a,
            concept=concepts[0],
            question_type=AssessmentQuestion.QuestionType.TRUE_FALSE,
            text="Is this true?",
            options=["True", "False"],
            correct_answer="True",
            order=1,
        )
        assert evaluate_answer(q, "true") is True
        assert evaluate_answer(q, "TRUE") is True
        assert evaluate_answer(q, "false") is False

    def test_drag_drop_list_comparison(self, course, concepts):
        a = Assessment.objects.create(course=course, title="DD Assessment")
        q = AssessmentQuestion.objects.create(
            assessment=a,
            concept=concepts[0],
            question_type=AssessmentQuestion.QuestionType.DRAG_DROP,
            text="Order these items",
            options=["A", "B", "C"],
            correct_answer=["A", "B", "C"],
            order=1,
        )
        assert evaluate_answer(q, ["A", "B", "C"]) is True
        assert evaluate_answer(q, ["C", "B", "A"]) is False


# ---------------------------------------------------------------------------
# submit_answer
# ---------------------------------------------------------------------------


class TestSubmitAnswer:
    def test_creates_response_with_is_correct(self, student, assessment):
        session = AssessmentSession.objects.create(
            student=student, assessment=assessment,
        )
        q = assessment.questions.first()
        resp = submit_answer(session, q.id, "A", time_taken=10)

        assert isinstance(resp, AssessmentResponse)
        assert resp.is_correct is True
        assert resp.answer == "A"
        assert resp.time_taken_seconds == 10

    def test_update_or_create_on_duplicate(self, student, assessment):
        session = AssessmentSession.objects.create(
            student=student, assessment=assessment,
        )
        q = assessment.questions.first()

        submit_answer(session, q.id, "B", time_taken=5)
        resp = submit_answer(session, q.id, "A", time_taken=8)

        assert resp.is_correct is True
        assert resp.time_taken_seconds == 8
        assert AssessmentResponse.objects.filter(
            session=session, question=q,
        ).count() == 1


# ---------------------------------------------------------------------------
# complete_assessment
# ---------------------------------------------------------------------------


class TestCompleteAssessment:
    @staticmethod
    def _make_session(student, assessment, answers):
        session = AssessmentSession.objects.create(
            student=student, assessment=assessment,
        )
        for q, ans in zip(assessment.questions.order_by("order"), answers):
            AssessmentResponse.objects.create(
                session=session,
                question=q,
                answer=ans,
                is_correct=evaluate_answer(q, ans),
                time_taken_seconds=10,
            )
        return session

    def test_sets_completed_status_and_timestamp(self, student, assessment):
        session = self._make_session(student, assessment, ["A", "A", "A"])
        complete_assessment(session.id, student.id)
        session.refresh_from_db()

        assert session.status == AssessmentSession.Status.COMPLETED
        assert session.completed_at is not None

    def test_score_all_correct(self, student, assessment):
        session = self._make_session(student, assessment, ["A", "A", "A"])
        complete_assessment(session.id, student.id)
        session.refresh_from_db()

        assert session.total_score == 100.0

    def test_score_half_correct(self, student, course, concepts):
        a = Assessment.objects.create(course=course, title="Two-Q Assessment")
        for i, c in enumerate(concepts[:2]):
            AssessmentQuestion.objects.create(
                assessment=a,
                concept=c,
                text=f"Q{i + 1}",
                options=["A", "B"],
                correct_answer="A",
                order=i + 1,
            )
        session = self._make_session(student, a, ["A", "B"])
        complete_assessment(session.id, student.id)
        session.refresh_from_db()

        assert session.total_score == 50.0

    def test_creates_learner_profile(self, student, assessment):
        session = self._make_session(student, assessment, ["A", "B", "B"])
        profile = complete_assessment(session.id, student.id)

        assert isinstance(profile, LearnerProfile)
        assert profile.student == student
        assert profile.course == assessment.course

    def test_profile_strengths_and_weaknesses(self, student, assessment):
        session = self._make_session(student, assessment, ["A", "B", "B"])
        profile = complete_assessment(session.id, student.id)

        concept_ids = list(
            assessment.questions.order_by("order")
            .values_list("concept_id", flat=True)
        )
        assert concept_ids[0] in profile.strengths
        assert concept_ids[1] in profile.weaknesses
        assert concept_ids[2] in profile.weaknesses

    def test_seeds_mastery_state_for_each_concept(self, student, assessment, concepts):
        session = self._make_session(student, assessment, ["A", "A", "A"])
        complete_assessment(session.id, student.id)

        for concept in concepts:
            assert MasteryState.objects.filter(
                student=student, concept=concept,
            ).exists()

    def test_initializes_student_pathway(self, student, assessment):
        session = self._make_session(student, assessment, ["A", "A", "A"])
        complete_assessment(session.id, student.id)

        assert StudentPathway.objects.filter(
            student=student, course=assessment.course,
        ).exists()
