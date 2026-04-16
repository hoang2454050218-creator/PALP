import logging
from django.db import transaction
from .models import Milestone, MicroTask

logger = logging.getLogger("palp")


class ProgressStatus:
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


def compute_milestone_progress(pathway, milestone):
    task_ids = set(
        milestone.tasks.filter(is_active=True).values_list("id", flat=True)
    )
    if not task_ids:
        return {
            "milestone_id": milestone.id,
            "completed": 0,
            "total": 0,
            "percentage": 0,
            "status": ProgressStatus.NOT_STARTED,
        }

    completed_set = set(pathway.tasks_completed or [])
    done = len(task_ids & completed_set)
    total = len(task_ids)
    pct = _safe_percentage(done, total)

    if done == 0:
        status = ProgressStatus.NOT_STARTED
    elif done >= total:
        status = ProgressStatus.COMPLETED
    else:
        status = ProgressStatus.IN_PROGRESS

    return {
        "milestone_id": milestone.id,
        "completed": done,
        "total": total,
        "percentage": pct,
        "status": status,
    }


def compute_course_progress(pathway):
    milestones = Milestone.objects.filter(
        course=pathway.course, is_active=True
    ).prefetch_related("tasks")

    milestone_results = []
    completed_milestones = 0
    total_milestones = milestones.count()

    for ms in milestones:
        result = compute_milestone_progress(pathway, ms)
        milestone_results.append(result)
        if result["status"] == ProgressStatus.COMPLETED:
            completed_milestones += 1

    return {
        "milestones": milestone_results,
        "completed_milestones": completed_milestones,
        "total_milestones": total_milestones,
        "percentage": _safe_percentage(completed_milestones, total_milestones),
    }


def mark_task_completed(pathway, task_id):
    tasks_done = list(pathway.tasks_completed or [])
    if task_id in tasks_done:
        return False

    tasks_done.append(task_id)
    pathway.tasks_completed = tasks_done
    _check_and_update_milestone_completion(pathway, task_id)
    pathway.save()
    return True


def _check_and_update_milestone_completion(pathway, task_id):
    try:
        task = MicroTask.objects.select_related("milestone").get(id=task_id)
    except MicroTask.DoesNotExist:
        return

    milestone = task.milestone
    all_task_ids = set(
        milestone.tasks.filter(is_active=True).values_list("id", flat=True)
    )
    completed_set = set(pathway.tasks_completed or [])

    if all_task_ids and all_task_ids.issubset(completed_set):
        ms_done = list(pathway.milestones_completed or [])
        if milestone.id not in ms_done:
            ms_done.append(milestone.id)
            pathway.milestones_completed = ms_done


def migrate_template_if_needed(pathway, milestone):
    known_versions = pathway.last_known_template_versions or {}
    known_ver = known_versions.get(str(milestone.id), 0)

    if known_ver >= milestone.template_version:
        return None

    current_task_ids = set(
        milestone.tasks.filter(is_active=True).values_list("id", flat=True)
    )
    completed_set = set(pathway.tasks_completed or [])

    preserved = completed_set & current_task_ids
    removed = completed_set - current_task_ids
    removed_for_milestone = removed & set(
        MicroTask.objects.filter(
            milestone=milestone
        ).values_list("id", flat=True)
    )

    new_task_ids = current_task_ids - completed_set
    tasks_completed = [t for t in pathway.tasks_completed or [] if t not in removed_for_milestone]
    pathway.tasks_completed = tasks_completed

    ms_done = list(pathway.milestones_completed or [])
    if milestone.id in ms_done:
        if not current_task_ids.issubset(set(tasks_completed)):
            ms_done.remove(milestone.id)
            pathway.milestones_completed = ms_done

    known_versions[str(milestone.id)] = milestone.template_version
    pathway.last_known_template_versions = known_versions
    pathway.save()

    migration_report = {
        "milestone_id": milestone.id,
        "old_version": known_ver,
        "new_version": milestone.template_version,
        "preserved_tasks": list(preserved),
        "removed_tasks": list(removed_for_milestone),
        "new_tasks": list(new_task_ids),
    }
    logger.info("Template migration: %s", migration_report)
    return migration_report


def _safe_percentage(done, total):
    if total <= 0:
        return 0
    pct = round(done / total * 100, 1)
    return max(0, min(100, pct))
