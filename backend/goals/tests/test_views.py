from datetime import date

import pytest
from django.utils import timezone

from adaptive.models import MasteryState
from goals.models import CareerGoal, SemesterGoal, StrategyPlan, WeeklyGoal
from goals.services import monday_of

pytestmark = pytest.mark.django_db


class TestCareerGoalView:
    def test_anon_blocked(self, anon_api):
        resp = anon_api.get("/api/goals/career/")
        assert resp.status_code in (401, 403)

    def test_lecturer_blocked(self, lecturer_api):
        resp = lecturer_api.get("/api/goals/career/")
        assert resp.status_code == 403

    def test_get_204_when_missing(self, student_api):
        resp = student_api.get("/api/goals/career/")
        assert resp.status_code == 204

    def test_put_creates_then_get_returns(self, student_api):
        resp = student_api.put(
            "/api/goals/career/",
            data={"label": "Backend dev", "category": "software_backend", "horizon_months": 12},
            format="json",
        )
        assert resp.status_code == 200
        get_resp = student_api.get("/api/goals/career/")
        assert get_resp.status_code == 200
        assert get_resp.data["label"] == "Backend dev"

    def test_delete(self, student_api, student):
        CareerGoal.objects.create(student=student, label="x", category="other")
        resp = student_api.delete("/api/goals/career/")
        assert resp.status_code == 204
        assert not CareerGoal.objects.filter(student=student).exists()


class TestWeeklyGoalViewSet:
    def test_create(self, student_api):
        resp = student_api.post(
            "/api/goals/weekly/",
            data={
                "week_start": str(monday_of(timezone.localdate())),
                "target_minutes": 240,
                "target_concept_ids": [],
                "target_micro_task_count": 8,
            },
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["target_minutes"] == 240

    def test_only_own_goals_listed(self, student_api, student, student_b):
        WeeklyGoal.objects.create(
            student=student, week_start=monday_of(timezone.localdate()), target_minutes=200,
        )
        WeeklyGoal.objects.create(
            student=student_b, week_start=monday_of(timezone.localdate()), target_minutes=300,
        )
        resp = student_api.get("/api/goals/weekly/")
        assert resp.status_code == 200
        data = resp.data.get("results", resp.data)
        assert all(item["target_minutes"] != 300 for item in data)


class TestTodayPlanView:
    def test_anon_blocked(self, anon_api):
        resp = anon_api.get("/api/goals/today/")
        assert resp.status_code in (401, 403)

    def test_returns_empty_for_brand_new_student(self, student_api):
        resp = student_api.get("/api/goals/today/")
        assert resp.status_code == 200
        assert resp.data["items"] == []

    def test_returns_weak_concept_item(self, student_api, student, concepts, micro_tasks):
        MasteryState.objects.create(student=student, concept=concepts[0], p_mastery=0.2)
        resp = student_api.get("/api/goals/today/")
        assert resp.status_code == 200
        kinds = [it["kind"] for it in resp.data["items"]]
        assert "weak_concept" in kinds


class TestNorthStarView:
    def test_anon_blocked(self, anon_api):
        resp = anon_api.get("/api/goals/north-star/")
        assert resp.status_code in (401, 403)

    def test_returns_three_panel_structure(self, student_api):
        resp = student_api.get("/api/goals/north-star/")
        assert resp.status_code == 200
        for key in ("forethought", "performance", "reflection"):
            assert key in resp.data


class TestReflectionSubmitView:
    def test_blocks_unknown_weekly_goal(self, student_api):
        resp = student_api.post(
            "/api/goals/reflection/",
            data={"weekly_goal_id": 99999, "learned_text": "x"},
            format="json",
        )
        assert resp.status_code == 404

    def test_submits_for_own_goal(self, student_api, student):
        wg = WeeklyGoal.objects.create(
            student=student, week_start=monday_of(timezone.localdate()), target_minutes=200,
        )
        resp = student_api.post(
            "/api/goals/reflection/",
            data={
                "weekly_goal_id": wg.id,
                "learned_text": "Tôi học được X",
                "struggle_text": "Khó ở Y",
                "next_priority_text": "Ưu tiên Z",
                "effort_rating": 4,
            },
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["learned_text"] == "Tôi học được X"

    def test_other_student_cannot_submit_for_my_goal(self, student, student_b):
        from rest_framework.test import APIClient

        wg = WeeklyGoal.objects.create(
            student=student, week_start=monday_of(timezone.localdate()), target_minutes=200,
        )
        client = APIClient()
        client.force_authenticate(user=student_b)
        resp = client.post(
            "/api/goals/reflection/",
            data={"weekly_goal_id": wg.id, "learned_text": "x"},
            format="json",
        )
        assert resp.status_code == 404
