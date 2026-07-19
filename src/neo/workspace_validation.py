from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import ValidationError

JsonDocument = dict[str, Any]


def validate_cross_references(
    projects: dict[Path, JsonDocument],
    days: dict[Path, JsonDocument],
    *,
    pending: JsonDocument | None = None,
    someday: JsonDocument | None = None,
) -> None:
    project_map: dict[str, JsonDocument] = {}
    milestone_map: dict[str, tuple[str, JsonDocument]] = {}
    task_map: dict[str, tuple[str, str, JsonDocument]] = {}
    ids: set[str] = set()

    for path, project in projects.items():
        _unique(ids, project["project_id"], str(path))
        if path.name != f"{project['slug']}.json":
            raise ValidationError(f"Project filename must match slug: {path}")
        project_map[project["project_id"]] = project
        for milestone in project["milestones"]:
            _unique(ids, milestone["milestone_id"], str(path))
            milestone_map[milestone["milestone_id"]] = (project["project_id"], milestone)
            for task in milestone["tasks"]:
                _unique(ids, task["task_id"], str(path))
                task_map[task["task_id"]] = (
                    project["project_id"],
                    milestone["milestone_id"],
                    task,
                )
                for note in task["notes"]:
                    _unique(ids, note["note_id"], str(path))
        for decision in project["decisions"]:
            _unique(ids, decision["decision_id"], str(path))
        for history in project["status_history"]:
            _unique(ids, history["history_id"], str(path))

    active_days = 0
    open_sessions = 0
    for path, day in days.items():
        _unique(ids, day["day_id"], str(path))
        if path.name != f"{day['date']}.json" or path.parent.name != day["date"][:4]:
            raise ValidationError(f"Day path must match wake date: {path}")
        if day["status"] == "active":
            active_days += 1
        allocation = sum(item["planned_allocation"] for item in day["work_plan"])
        if day["workday_capacity"] is not None and allocation > day["workday_capacity"]:
            raise ValidationError(f"Plan exceeds workday capacity: {path}")
        for item in [*day["work_plan"], *day["work_sessions"]]:
            project_id = item["project_id"]
            milestone_id = item["milestone_id"]
            task_id = item["task_id"]
            if project_id not in project_map:
                raise ValidationError(f"Unknown project reference in {path}: {project_id}")
            if milestone_id not in milestone_map or milestone_map[milestone_id][0] != project_id:
                raise ValidationError(f"Invalid milestone reference in {path}: {milestone_id}")
            if task_id not in task_map or task_map[task_id][:2] != (project_id, milestone_id):
                raise ValidationError(f"Invalid task reference in {path}: {task_id}")
        for item in day["work_plan"]:
            _unique(ids, item["plan_item_id"], str(path))
        for session in day["work_sessions"]:
            _unique(ids, session["session_id"], str(path))
            if session["checked_out_at"] is None:
                open_sessions += 1
        for note in day["notes"]:
            _unique(ids, note["note_id"], str(path))
        for todo in day["todolist"]:
            _unique(ids, todo["todo_id"], str(path))
        for meal in day["meals"]:
            _unique(ids, meal["meal_id"], str(path))
        for outing in day["outings"]:
            _unique(ids, outing["outing_id"], str(path))

    for item in (pending or {}).get("items", []):
        _unique(ids, item["pending_id"], "data/pending.json")
    for item in (someday or {}).get("items", []):
        _unique(ids, item["someday_id"], "data/someday.json")

    if active_days > 1:
        raise ValidationError("More than one active life day exists")
    if open_sessions > 1:
        raise ValidationError("More than one open work session exists")


def _unique(registry: set[str], value: str, path: str) -> None:
    if value in registry:
        raise ValidationError(f"Duplicate UUID {value} in {path}")
    registry.add(value)
