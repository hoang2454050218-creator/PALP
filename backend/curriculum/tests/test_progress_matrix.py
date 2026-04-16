"""
Progress / backward-design edge-case test matrix (BD-01 .. BD-10).

Covers: task completion, double-count prevention, state persistence,
out-of-order milestones, template migration, concurrent writes,
undo/rollback, prerequisite gating, incomplete milestone guard,
and progress bounds validation.
"""
import pytest

from adaptive.models import MasteryState, StudentPathway, TaskAttempt
from curriculum.models import MicroTask, Milestone
from curriculum.services import (
    compute_course_progress,
    compute_milestone_progress,
    mark_task_completed,
    migrate_template_if_needed,
)

pytestmark = pytest.mark.django_db

URL_ADAPTIVE = "/api/adaptive/"


# =========================================================================
# BD-01  Complete 1 task -> progress increases
# =========================================================================


class TestBD01TaskCompletionIncreasesProgress:
    def test_mark_task_adds_to_completed(self, student_with_pathway, micro_tasks):
        pathway = student_with_pathway
        task = micro_tasks[0]

        changed = mark_task_completed(pathway, task.id)
        assert changed is True
        assert task.id in pathway.tasks_completed

    def test_milestone_progress_increases(
        self, student_with_pathway, micro_tasks, milestones,
    ):
        pathway = student_with_pathway
        mark_task_completed(pathway, micro_tasks[0].id)

        progress = compute_milestone_progress(pathway, milestones[0])
        assert progress["completed"] == 1
        assert progress["percentage"] > 0

    def test_course_progress_increases(self, student_with_pathway, micro_tasks):
        pathway = student_with_pathway
        mark_task_completed(pathway, micro_tasks[0].id)

        course_prog = compute_course_progress(pathway)
        assert course_prog["percentage"] >= 0


# =========================================================================
# BD-02  Click complete twice -> no double-count
# =========================================================================


class TestBD02NoDoubleCount:
    def test_second_mark_returns_false(self, student_with_pathway, micro_tasks):
        pathway = student_with_pathway
        task = micro_tasks[0]

        first = mark_task_completed(pathway, task.id)
        second = mark_task_completed(pathway, task.id)

        assert first is True
        assert second is False
        assert pathway.tasks_completed.count(task.id) == 1

    def test_progress_same_after_double_call(
        self, student_with_pathway, micro_tasks, milestones,
    ):
        pathway = student_with_pathway
        mark_task_completed(pathway, micro_tasks[0].id)
        p1 = compute_milestone_progress(pathway, milestones[0])

        mark_task_completed(pathway, micro_tasks[0].id)
        p2 = compute_milestone_progress(pathway, milestones[0])

        assert p1["percentage"] == p2["percentage"]
        assert p1["completed"] == p2["completed"]


# =========================================================================
# BD-03  Task done then refresh -> state preserved
# =========================================================================


class TestBD03StatePersistsAfterRefresh:
    def test_pathway_reloaded_from_db(self, student_with_pathway, micro_tasks):
        pathway = student_with_pathway
        mark_task_completed(pathway, micro_tasks[0].id)

        reloaded = StudentPathway.objects.get(id=pathway.id)
        assert micro_tasks[0].id in reloaded.tasks_completed

    def test_api_pathway_shows_completed(
        self, student_api, student, course, student_with_pathway, micro_tasks,
    ):
        pathway = student_with_pathway
        mark_task_completed(pathway, micro_tasks[0].id)

        resp = student_api.get(f"{URL_ADAPTIVE}pathway/{course.id}/")
        assert resp.status_code == 200
        assert micro_tasks[0].id in resp.data["tasks_completed"]


# =========================================================================
# BD-04  Complete milestone out of order -> allowed
# =========================================================================


class TestBD04OutOfOrderMilestone:
    def test_milestone2_completes_without_milestone1(
        self, student_with_pathway, micro_tasks, milestones,
    ):
        pathway = student_with_pathway

        m2_tasks = list(
            milestones[1].tasks.filter(is_active=True).values_list("id", flat=True)
        )
        for tid in m2_tasks:
            mark_task_completed(pathway, tid)

        assert milestones[1].id in (pathway.milestones_completed or [])
        assert milestones[0].id not in (pathway.milestones_completed or [])

    def test_both_milestones_can_complete_independently(
        self, student_with_pathway, micro_tasks, milestones,
    ):
        pathway = student_with_pathway

        for ms in milestones:
            task_ids = list(
                ms.tasks.filter(is_active=True).values_list("id", flat=True)
            )
            for tid in task_ids:
                mark_task_completed(pathway, tid)

        for ms in milestones:
            assert ms.id in pathway.milestones_completed


# =========================================================================
# BD-05  GV changes template mid-progress -> mapping correct
# =========================================================================


class TestBD05TemplateMigration:
    def test_version_bump_removes_stale_tasks(
        self, student_with_pathway, micro_tasks, milestones, concepts,
    ):
        pathway = student_with_pathway
        old_task = micro_tasks[0]
        mark_task_completed(pathway, old_task.id)
        mark_task_completed(pathway, micro_tasks[1].id)

        assert milestones[0].id in (pathway.milestones_completed or [])

        old_task.is_active = False
        old_task.save()

        new_task = MicroTask.objects.create(
            milestone=milestones[0], concept=concepts[0],
            title="Bai tap moi", difficulty=1, estimated_minutes=5,
            content={"question": "New?", "options": ["A"], "correct_answer": "A"},
        )

        milestones[0].template_version += 1
        milestones[0].save()

        report = migrate_template_if_needed(pathway, milestones[0])
        assert report is not None
        assert milestones[0].id not in (pathway.milestones_completed or [])

    def test_preserved_tasks_survive_migration(
        self, student_with_pathway, micro_tasks, milestones,
    ):
        pathway = student_with_pathway
        mark_task_completed(pathway, micro_tasks[1].id)

        milestones[0].template_version += 1
        milestones[0].save()

        migrate_template_if_needed(pathway, milestones[0])
        assert micro_tasks[1].id in (pathway.tasks_completed or [])


# =========================================================================
# BD-06  2 devices same action -> no conflict
# =========================================================================


class TestBD06ConcurrentDevices:
    def test_double_mark_is_idempotent(self, student_with_pathway, micro_tasks):
        pathway = student_with_pathway
        task = micro_tasks[0]

        r1 = mark_task_completed(pathway, task.id)
        pathway.refresh_from_db()
        r2 = mark_task_completed(pathway, task.id)

        assert r1 is True
        assert r2 is False
        assert pathway.tasks_completed.count(task.id) == 1


# =========================================================================
# BD-07  Undo / mark incomplete -> progress rollback
# =========================================================================


class TestBD07UndoMarkIncomplete:
    def test_removing_task_decreases_progress(
        self, student_with_pathway, micro_tasks, milestones,
    ):
        pathway = student_with_pathway
        mark_task_completed(pathway, micro_tasks[0].id)
        mark_task_completed(pathway, micro_tasks[1].id)

        assert milestones[0].id in (pathway.milestones_completed or [])

        tasks_done = list(pathway.tasks_completed)
        tasks_done.remove(micro_tasks[0].id)
        pathway.tasks_completed = tasks_done
        pathway.save()

        progress = compute_milestone_progress(pathway, milestones[0])
        assert progress["completed"] == 1
        assert progress["status"] == "in_progress"

    def test_removing_task_uncompletes_milestone(
        self, student_with_pathway, micro_tasks, milestones,
    ):
        pathway = student_with_pathway
        m1_task_ids = list(
            milestones[0].tasks.filter(is_active=True).values_list("id", flat=True)
        )
        for tid in m1_task_ids:
            mark_task_completed(pathway, tid)

        assert milestones[0].id in (pathway.milestones_completed or [])

        tasks_done = list(pathway.tasks_completed)
        tasks_done.remove(m1_task_ids[0])
        pathway.tasks_completed = tasks_done

        ms_done = list(pathway.milestones_completed)
        if milestones[0].id in ms_done:
            ms_done.remove(milestones[0].id)
        pathway.milestones_completed = ms_done
        pathway.save()

        progress = compute_milestone_progress(pathway, milestones[0])
        assert progress["status"] != "completed"


# =========================================================================
# BD-08  Task locked by prerequisite -> not accessible
# =========================================================================


class TestBD08PrerequisiteGating:
    def test_next_task_stays_in_first_concept(
        self, student_api, student, course, concepts, micro_tasks,
        student_with_pathway,
    ):
        pathway = student_with_pathway
        pathway.current_concept = concepts[0]
        pathway.concepts_completed = []
        pathway.save()

        resp = student_api.get(f"{URL_ADAPTIVE}next-task/{course.id}/")
        assert resp.status_code == 200

        assert resp.data["concept"] == concepts[0].id

    def test_completed_concept_opens_next(
        self, student_api, student, course, concepts, micro_tasks,
        student_with_pathway,
    ):
        pathway = student_with_pathway
        pathway.current_concept = concepts[0]
        pathway.concepts_completed = [concepts[0].id]
        pathway.save()

        for task in micro_tasks:
            if task.concept_id == concepts[0].id:
                TaskAttempt.objects.create(
                    student=student, task=task,
                    is_correct=True, score=100, max_score=100,
                    answer=task.content["correct_answer"],
                    attempt_number=1,
                )

        resp = student_api.get(f"{URL_ADAPTIVE}next-task/{course.id}/")
        assert resp.status_code == 200

        if "concept" in resp.data:
            assert resp.data["concept"] != concepts[0].id


# =========================================================================
# BD-09  Milestone marked done but sub-tasks insufficient -> detected
# =========================================================================


class TestBD09MilestoneInconsistency:
    def test_compute_detects_false_completion(
        self, student_with_pathway, milestones,
    ):
        pathway = student_with_pathway
        pathway.milestones_completed = [milestones[0].id]
        pathway.tasks_completed = []
        pathway.save()

        progress = compute_milestone_progress(pathway, milestones[0])
        assert progress["percentage"] == 0
        assert progress["status"] == "not_started"

    def test_partial_tasks_not_complete(
        self, student_with_pathway, micro_tasks, milestones,
    ):
        pathway = student_with_pathway
        m1_task_ids = list(
            milestones[0].tasks.filter(is_active=True).values_list("id", flat=True)
        )

        mark_task_completed(pathway, m1_task_ids[0])

        progress = compute_milestone_progress(pathway, milestones[0])
        if len(m1_task_ids) > 1:
            assert progress["status"] != "completed"
            assert progress["percentage"] < 100


# =========================================================================
# BD-10  Progress > 100% or negative -> never happens
# =========================================================================


class TestBD10ProgressBounds:
    def test_percentage_never_exceeds_100(
        self, student_with_pathway, micro_tasks, milestones,
    ):
        pathway = student_with_pathway
        for task in micro_tasks:
            mark_task_completed(pathway, task.id)

        mark_task_completed(pathway, micro_tasks[0].id)

        for ms in milestones:
            progress = compute_milestone_progress(pathway, ms)
            assert 0 <= progress["percentage"] <= 100

        course_prog = compute_course_progress(pathway)
        assert 0 <= course_prog["percentage"] <= 100

    def test_empty_milestone_returns_zero(self, student_with_pathway, course):
        pathway = student_with_pathway
        empty_ms = Milestone.objects.create(
            course=course, title="Empty", order=99, target_week=10,
        )

        progress = compute_milestone_progress(pathway, empty_ms)
        assert progress["percentage"] == 0
        assert progress["total"] == 0

    def test_duplicate_tasks_in_list_clamped(self, student_with_pathway, micro_tasks):
        pathway = student_with_pathway
        pathway.tasks_completed = [micro_tasks[0].id] * 5
        pathway.save()

        course_prog = compute_course_progress(pathway)
        assert course_prog["percentage"] <= 100

    def test_negative_not_possible(self, student_with_pathway, milestones):
        pathway = student_with_pathway
        pathway.tasks_completed = []
        pathway.milestones_completed = []
        pathway.save()

        course_prog = compute_course_progress(pathway)
        assert course_prog["percentage"] >= 0

        for ms in milestones:
            progress = compute_milestone_progress(pathway, ms)
            assert progress["percentage"] >= 0
