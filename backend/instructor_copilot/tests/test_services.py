"""Co-pilot tests — generate + draft + approve + RBAC."""
from __future__ import annotations

from datetime import date

import pytest

from instructor_copilot.models import FeedbackDraft, GeneratedExercise
from instructor_copilot.services import (
    approve_exercise,
    draft_feedback,
    generate_exercise,
)


pytestmark = pytest.mark.django_db


class TestGenerateExercise:
    def test_creates_draft(self, course, concepts, lecturer):
        ex = generate_exercise(
            course=course, concept=concepts[0],
            requested_by=lecturer, difficulty=2,
        )
        assert isinstance(ex, GeneratedExercise)
        assert ex.status == GeneratedExercise.Status.DRAFT
        assert ex.title

    def test_template_picked_per_difficulty(self, course, concepts, lecturer):
        easy = generate_exercise(
            course=course, concept=concepts[0],
            requested_by=lecturer, difficulty=1,
        )
        hard = generate_exercise(
            course=course, concept=concepts[1],
            requested_by=lecturer, difficulty=3,
        )
        assert easy.template_key == "concept_check_easy"
        assert hard.template_key == "synthesis_hard"

    def test_body_has_options_and_correct_answer(self, course, concepts, lecturer):
        ex = generate_exercise(
            course=course, concept=concepts[0],
            requested_by=lecturer, difficulty=2,
        )
        assert "options" in ex.body
        assert ex.body["correct_answer"] in ex.body["options"]


class TestApproveExercise:
    def test_promotes_to_micro_task(
        self, course, concepts, milestones, lecturer,
    ):
        ex = generate_exercise(
            course=course, concept=concepts[0],
            requested_by=lecturer, difficulty=2,
        )
        approve_exercise(exercise=ex, reviewer=lecturer, notes="ok")
        ex.refresh_from_db()
        assert ex.status == GeneratedExercise.Status.PUBLISHED
        assert ex.published_micro_task_id is not None

    def test_no_milestone_raises(self, course, concepts, lecturer):
        # No milestones fixture loaded -> approve must raise.
        ex = generate_exercise(
            course=course, concept=concepts[0],
            requested_by=lecturer, difficulty=2,
        )
        with pytest.raises(ValueError):
            approve_exercise(exercise=ex, reviewer=lecturer)


class TestDraftFeedback:
    def test_creates_draft_with_summary(
        self, student, lecturer, class_with_members, concepts,
    ):
        draft = draft_feedback(
            student=student, requested_by=lecturer, week_start=date(2026, 4, 13),
        )
        assert isinstance(draft, FeedbackDraft)
        assert "Tuần 2026-04-13" in draft.summary

    def test_idempotent(self, student, lecturer, class_with_members):
        d1 = draft_feedback(student=student, requested_by=lecturer, week_start=date(2026, 4, 13))
        d2 = draft_feedback(student=student, requested_by=lecturer, week_start=date(2026, 4, 13))
        assert d1.id == d2.id


class TestViews:
    def test_generate_endpoint_lecturer_only(self, student_api, course, concepts):
        resp = student_api.post(
            "/api/copilot/exercises/generate/",
            {"course_id": course.id, "concept_id": concepts[0].id, "difficulty": 2},
            format="json",
        )
        assert resp.status_code == 403

    def test_generate_endpoint_lecturer(self, lecturer_api, course, concepts):
        resp = lecturer_api.post(
            "/api/copilot/exercises/generate/",
            {"course_id": course.id, "concept_id": concepts[0].id, "difficulty": 2},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["title"]

    def test_approve_endpoint(
        self, lecturer_api, course, concepts, milestones,
    ):
        gen_resp = lecturer_api.post(
            "/api/copilot/exercises/generate/",
            {"course_id": course.id, "concept_id": concepts[0].id, "difficulty": 2},
            format="json",
        )
        exercise_id = gen_resp.data["id"]
        approve_resp = lecturer_api.post(
            f"/api/copilot/exercises/{exercise_id}/approve/",
            {"notes": "ok"},
            format="json",
        )
        assert approve_resp.status_code == 200
        assert approve_resp.data["status"] == "published"

    def test_feedback_draft_endpoint(
        self, lecturer_api, student, class_with_members,
    ):
        resp = lecturer_api.post(
            "/api/copilot/feedback/draft/",
            {"student_id": student.id, "week_start": "2026-04-13"},
            format="json",
        )
        assert resp.status_code == 201
        assert "summary" in resp.data
