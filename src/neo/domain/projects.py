from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..errors import ConflictError, ValidationError
from ..utils import new_uuid, now_iso

PROJECT_STATUSES = {"draft", "active", "waiting", "paused", "complete", "cancelled"}
MILESTONE_STATUSES = {"planned", "active", "complete", "cancelled"}
TASK_STATUSES = {"todo", "in_progress", "waiting", "done", "cancelled"}


def create_project(title: str, slug: str, description: str = "") -> dict[str, Any]:
    timestamp = now_iso()
    project_id = new_uuid()
    return {
        "schema_version": 1,
        "project_id": project_id,
        "title": title.strip(),
        "slug": slug,
        "description": description.strip(),
        "status": "draft",
        "waiting": None,
        "pause": None,
        "created_at": timestamp,
        "updated_at": timestamp,
        "current_milestone_id": None,
        "deadline_calendar_event_id": None,
        "milestones": [],
        "decisions": [],
        "status_history": [
            {
                "history_id": new_uuid(),
                "occurred_at": timestamp,
                "from": None,
                "to": "draft",
                "reason": "project created",
            }
        ],
    }


def rename_project(project: dict[str, Any], title: str, slug: str | None = None) -> dict[str, Any]:
    result = deepcopy(project)
    result["title"] = title.strip()
    if slug is not None:
        result["slug"] = slug
    result["updated_at"] = now_iso()
    return result


def set_project_status(
    project: dict[str, Any],
    status: str,
    *,
    reason: str | None = None,
    waiting_on: str | None = None,
    next_review_at: str | None = None,
    pause_reason: str | None = None,
    resume_condition: str | None = None,
) -> dict[str, Any]:
    if status not in PROJECT_STATUSES:
        raise ValidationError(f"Unknown project status: {status}")
    result = deepcopy(project)
    previous = result["status"]
    timestamp = now_iso()
    if status == "waiting":
        if not waiting_on:
            raise ValidationError("waiting status requires --waiting-on")
        result["waiting"] = {
            "on": waiting_on,
            "since": timestamp,
            "next_review_at": next_review_at,
        }
        result["pause"] = None
    elif status == "paused":
        if not pause_reason:
            raise ValidationError("paused status requires --pause-reason")
        result["pause"] = {
            "reason": pause_reason,
            "since": timestamp,
            "resume_condition": resume_condition,
        }
        result["waiting"] = None
    else:
        result["waiting"] = None
        result["pause"] = None

    if status == "complete":
        open_tasks = [
            task["title"]
            for milestone in result["milestones"]
            for task in milestone["tasks"]
            if task["status"] not in {"done", "cancelled"}
        ]
        if open_tasks:
            raise ConflictError("Cannot complete a project with open tasks")

    result["status"] = status
    result["updated_at"] = timestamp
    if previous != status:
        result["status_history"].append(
            {
                "history_id": new_uuid(),
                "occurred_at": timestamp,
                "from": previous,
                "to": status,
                "reason": reason,
            }
        )
    return result


def add_milestone(project: dict[str, Any], title: str, remaining_effort: float) -> tuple[dict[str, Any], str]:
    _validate_effort(remaining_effort)
    result = deepcopy(project)
    timestamp = now_iso()
    milestone_id = new_uuid()
    milestone = {
        "milestone_id": milestone_id,
        "title": title.strip(),
        "status": "planned" if result["milestones"] else "active",
        "remaining_effort": remaining_effort,
        "calendar_event_id": None,
        "created_at": timestamp,
        "updated_at": timestamp,
        "tasks": [],
    }
    result["milestones"].append(milestone)
    if result["current_milestone_id"] is None:
        result["current_milestone_id"] = milestone_id
    result["updated_at"] = timestamp
    return result, milestone_id


def set_milestone_status(project: dict[str, Any], milestone_id: str, status: str) -> dict[str, Any]:
    if status not in MILESTONE_STATUSES:
        raise ValidationError(f"Unknown milestone status: {status}")
    result = deepcopy(project)
    milestone = _find_milestone(result, milestone_id)
    if status == "planned" and result["current_milestone_id"] == milestone_id:
        raise ConflictError("Current milestone cannot be moved back to planned without activating another milestone")
    if status == "complete":
        open_tasks = [task for task in milestone["tasks"] if task["status"] not in {"done", "cancelled"}]
        if open_tasks:
            raise ConflictError("Cannot complete a milestone with open tasks")
        milestone["remaining_effort"] = 0
    milestone["status"] = status
    milestone["updated_at"] = now_iso()
    result["updated_at"] = milestone["updated_at"]
    if status == "active":
        for other in result["milestones"]:
            if other["milestone_id"] != milestone_id and other["status"] == "active":
                other["status"] = "planned"
                other["updated_at"] = milestone["updated_at"]
        result["current_milestone_id"] = milestone_id
    elif result["current_milestone_id"] == milestone_id and status in {"complete", "cancelled"}:
        next_open = next(
            (item for item in result["milestones"] if item["status"] == "planned"),
            None,
        )
        if next_open:
            next_open["status"] = "active"
            next_open["updated_at"] = milestone["updated_at"]
            result["current_milestone_id"] = next_open["milestone_id"]
        else:
            result["current_milestone_id"] = None
    return result


def set_milestone_effort(project: dict[str, Any], milestone_id: str, value: float) -> dict[str, Any]:
    _validate_effort(value)
    result = deepcopy(project)
    milestone = _find_milestone(result, milestone_id)
    milestone["remaining_effort"] = value
    milestone["updated_at"] = now_iso()
    result["updated_at"] = milestone["updated_at"]
    return result


def link_milestone_calendar(project: dict[str, Any], milestone_id: str, event_id: str | None) -> dict[str, Any]:
    result = deepcopy(project)
    milestone = _find_milestone(result, milestone_id)
    milestone["calendar_event_id"] = event_id
    milestone["updated_at"] = now_iso()
    result["updated_at"] = milestone["updated_at"]
    return result


def link_deadline_calendar(project: dict[str, Any], event_id: str | None) -> dict[str, Any]:
    result = deepcopy(project)
    result["deadline_calendar_event_id"] = event_id
    result["updated_at"] = now_iso()
    return result


def add_task(project: dict[str, Any], milestone_id: str, title: str) -> tuple[dict[str, Any], str]:
    result = deepcopy(project)
    milestone = _find_milestone(result, milestone_id)
    timestamp = now_iso()
    task_id = new_uuid()
    milestone["tasks"].append(
        {
            "task_id": task_id,
            "title": title.strip(),
            "status": "todo",
            "waiting": None,
            "created_at": timestamp,
            "updated_at": timestamp,
            "completed_at": None,
            "notes": [],
        }
    )
    milestone["updated_at"] = timestamp
    result["updated_at"] = timestamp
    return result, task_id


def set_task_status(
    project: dict[str, Any],
    task_id: str,
    status: str,
    *,
    waiting_on: str | None = None,
) -> dict[str, Any]:
    if status not in TASK_STATUSES:
        raise ValidationError(f"Unknown task status: {status}")
    result = deepcopy(project)
    milestone, task = _find_task(result, task_id)
    timestamp = now_iso()
    task["status"] = status
    task["updated_at"] = timestamp
    if status == "waiting":
        if not waiting_on:
            raise ValidationError("waiting task requires --waiting-on")
        task["waiting"] = {"on": waiting_on, "since": timestamp}
    else:
        task["waiting"] = None
    task["completed_at"] = timestamp if status == "done" else None
    milestone["updated_at"] = timestamp
    result["updated_at"] = timestamp
    return result


def add_task_note(project: dict[str, Any], task_id: str, text: str) -> dict[str, Any]:
    result = deepcopy(project)
    milestone, task = _find_task(result, task_id)
    timestamp = now_iso()
    task["notes"].append({"note_id": new_uuid(), "occurred_at": timestamp, "text": text.strip()})
    task["updated_at"] = timestamp
    milestone["updated_at"] = timestamp
    result["updated_at"] = timestamp
    return result


def add_decision(project: dict[str, Any], title: str, detail: str) -> dict[str, Any]:
    result = deepcopy(project)
    timestamp = now_iso()
    result["decisions"].append(
        {
            "decision_id": new_uuid(),
            "occurred_at": timestamp,
            "title": title.strip(),
            "detail": detail.strip(),
        }
    )
    result["updated_at"] = timestamp
    return result


def _find_milestone(project: dict[str, Any], milestone_id: str) -> dict[str, Any]:
    for milestone in project["milestones"]:
        if milestone["milestone_id"] == milestone_id:
            return milestone
    raise ValidationError(f"Milestone does not belong to project: {milestone_id}")


def _find_task(project: dict[str, Any], task_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    for milestone in project["milestones"]:
        for task in milestone["tasks"]:
            if task["task_id"] == task_id:
                return milestone, task
    raise ValidationError(f"Task does not belong to project: {task_id}")


def _validate_effort(value: float) -> None:
    if value < 0 or round(value * 2) != value * 2:
        raise ValidationError("remaining_effort must be a non-negative multiple of 0.5")
