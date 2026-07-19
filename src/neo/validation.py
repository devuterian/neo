from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from .paths import NeoPaths
from .transaction import read_json

SEOUL = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class Issue:
    severity: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"severity": self.severity, "path": self.path, "message": self.message}


def _load_schema(paths: NeoPaths, name: str) -> dict[str, Any]:
    return read_json(paths.schemas / name)


def _schema_registry(paths: NeoPaths) -> Registry:
    registry = Registry()
    for schema_path in paths.schemas.glob("*.json"):
        schema = read_json(schema_path)
        schema_id = schema.get("$id")
        if schema_id:
            registry = registry.with_resource(schema_id, Resource.from_contents(schema))
    return registry


def schema_issues(paths: NeoPaths, document: Any, schema_name: str, label: str) -> list[Issue]:
    schema = _load_schema(paths, schema_name)
    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
        registry=_schema_registry(paths),
    )
    issues: list[Issue] = []
    for error in sorted(validator.iter_errors(document), key=lambda item: list(item.absolute_path)):
        pointer = "/".join(str(part) for part in error.absolute_path)
        location = f"{label}/{pointer}" if pointer else label
        issues.append(Issue("error", location, error.message))
    return issues


def validate_document(paths: NeoPaths, document: Any, schema_name: str, label: str) -> None:
    issues = schema_issues(paths, document, schema_name, label)
    if issues:
        rendered = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        raise ValueError(rendered)


def _iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def validate_all(paths: NeoPaths) -> list[Issue]:
    issues: list[Issue] = []

    try:
        config = read_json(paths.config)
        issues.extend(schema_issues(paths, config, "app.schema.json", "config/app.json"))
    except Exception as exc:
        issues.append(Issue("error", "config/app.json", f"Cannot read JSON: {exc}"))

    projects: dict[str, tuple[Path, dict[str, Any]]] = {}
    milestones: dict[str, tuple[str, dict[str, Any]]] = {}
    tasks: dict[str, tuple[str, str, dict[str, Any]]] = {}
    all_ids: dict[str, str] = {}
    calendar_links: dict[str, str] = {}

    for path in sorted(paths.projects.glob("*.json")):
        label = path.relative_to(paths.root).as_posix()
        try:
            project = read_json(path)
        except Exception as exc:
            issues.append(Issue("error", label, f"Cannot read JSON: {exc}"))
            continue
        issues.extend(schema_issues(paths, project, "project.schema.json", label))
        project_id = project.get("project_id")
        if not isinstance(project_id, str):
            continue
        projects[project_id] = (path, project)
        expected_name = f"{project.get('slug', '')}.json"
        if path.name != expected_name:
            issues.append(Issue("error", label, f"Filename must be {expected_name}"))
        _register_id(all_ids, project_id, f"{label}:project", issues)

        status = project.get("status")
        waiting = project.get("waiting")
        pause = project.get("pause")
        if status == "waiting" and waiting is None:
            issues.append(Issue("error", label, "waiting project requires waiting details"))
        if status != "waiting" and waiting is not None:
            issues.append(Issue("error", label, "waiting details are only valid for waiting status"))
        if status == "paused" and pause is None:
            issues.append(Issue("error", label, "paused project requires pause details"))
        if status != "paused" and pause is not None:
            issues.append(Issue("error", label, "pause details are only valid for paused status"))

        deadline_event = project.get("deadline_calendar_event_id")
        if deadline_event:
            _register_calendar_link(calendar_links, deadline_event, f"{label}:deadline", issues)

        local_milestone_ids: set[str] = set()
        for milestone in project.get("milestones", []):
            milestone_id = milestone.get("milestone_id")
            if not isinstance(milestone_id, str):
                continue
            local_milestone_ids.add(milestone_id)
            milestones[milestone_id] = (project_id, milestone)
            _register_id(all_ids, milestone_id, f"{label}:milestone", issues)
            event_id = milestone.get("calendar_event_id")
            if event_id:
                _register_calendar_link(calendar_links, event_id, f"{label}:milestone", issues)
            for task in milestone.get("tasks", []):
                task_id = task.get("task_id")
                if not isinstance(task_id, str):
                    continue
                tasks[task_id] = (project_id, milestone_id, task)
                _register_id(all_ids, task_id, f"{label}:task", issues)
                task_status = task.get("status")
                task_waiting = task.get("waiting")
                if task_status == "waiting" and task_waiting is None:
                    issues.append(Issue("error", label, f"Task {task_id} requires waiting details"))
                if task_status != "waiting" and task_waiting is not None:
                    issues.append(Issue("error", label, f"Task {task_id} has invalid waiting details"))
                if task_status == "done" and task.get("completed_at") is None:
                    issues.append(Issue("error", label, f"Task {task_id} is done without completed_at"))
                if task_status != "done" and task.get("completed_at") is not None:
                    issues.append(Issue("error", label, f"Task {task_id} has completed_at but is not done"))
                for note in task.get("notes", []):
                    note_id = note.get("note_id")
                    if isinstance(note_id, str):
                        _register_id(all_ids, note_id, f"{label}:task-note", issues)
        for decision in project.get("decisions", []):
            decision_id = decision.get("decision_id")
            if isinstance(decision_id, str):
                _register_id(all_ids, decision_id, f"{label}:decision", issues)
        for history in project.get("status_history", []):
            history_id = history.get("history_id")
            if isinstance(history_id, str):
                _register_id(all_ids, history_id, f"{label}:status-history", issues)
        current_milestone_id = project.get("current_milestone_id")
        if current_milestone_id is not None and current_milestone_id not in local_milestone_ids:
            issues.append(Issue("error", label, "current_milestone_id does not belong to the project"))
        active_milestones = [m for m in project.get("milestones", []) if m.get("status") == "active"]
        if len(active_milestones) > 1:
            issues.append(Issue("error", label, "More than one active milestone exists"))
        if current_milestone_id is not None:
            current = next((m for m in project.get("milestones", []) if m.get("milestone_id") == current_milestone_id), None)
            if current is not None and current.get("status") != "active":
                issues.append(Issue("error", label, "current_milestone_id must point to an active milestone"))
        elif active_milestones:
            issues.append(Issue("error", label, "Active milestone exists without current_milestone_id"))
        for milestone in project.get("milestones", []):
            if milestone.get("status") == "complete" and milestone.get("remaining_effort") != 0:
                issues.append(Issue("error", label, f"Completed milestone {milestone.get('milestone_id')} must have zero remaining effort"))

    active_days: list[tuple[Path, dict[str, Any]]] = []
    open_sessions: list[tuple[Path, dict[str, Any], dict[str, Any]]] = []
    days: dict[str, tuple[Path, dict[str, Any]]] = {}

    for path in sorted(paths.days.glob("*/*.json")):
        label = path.relative_to(paths.root).as_posix()
        try:
            day = read_json(path)
        except Exception as exc:
            issues.append(Issue("error", label, f"Cannot read JSON: {exc}"))
            continue
        schema_version = day.get("schema_version")
        if schema_version == 2:
            issues.extend(schema_issues(paths, day, "day.schema.json", label))
        elif schema_version == 1:
            issues.append(Issue("warning", label, "day schema_version 1; run neoctl migrate to upgrade to v2"))
        elif schema_version is not None:
            issues.append(Issue("error", label, f"unknown day schema_version {schema_version}"))
        else:
            issues.append(Issue("warning", label, "day missing schema_version; assuming v1"))
        day_id = day.get("day_id")
        if isinstance(day_id, str):
            days[day_id] = (path, day)
            _register_id(all_ids, day_id, f"{label}:day", issues)

        date_value = day.get("date")
        if isinstance(date_value, str):
            expected = paths.days / date_value[:4] / f"{date_value}.json"
            if path.resolve() != expected.resolve():
                issues.append(Issue("error", label, f"Day file must be {expected.relative_to(paths.root)}"))
        wake_at = day.get("wake_at")
        if isinstance(wake_at, str) and isinstance(date_value, str):
            try:
                wake_date = _iso(wake_at).astimezone(SEOUL).date().isoformat()
                if wake_date != date_value:
                    issues.append(Issue("error", label, "date must equal wake_at date in Asia/Seoul"))
            except ValueError:
                pass

        if day.get("status") == "active":
            active_days.append((path, day))
        capacity = day.get("workday_capacity")
        allocation = sum(item.get("planned_allocation", 0) for item in day.get("work_plan", []))
        if capacity is not None and allocation > capacity:
            issues.append(Issue("error", label, "planned allocation exceeds workday_capacity"))
        if capacity == 0 and day.get("work_plan"):
            issues.append(Issue("error", label, "workday_capacity 0 cannot have planned tasks"))

        seen_plan_tasks: set[str] = set()
        for item in day.get("work_plan", []):
            task_id = item.get("task_id")
            if task_id in seen_plan_tasks:
                issues.append(Issue("error", label, f"Task {task_id} appears more than once in plan"))
            if isinstance(task_id, str):
                seen_plan_tasks.add(task_id)
            _validate_reference(item, label, projects, milestones, tasks, issues)
            plan_id = item.get("plan_item_id")
            if isinstance(plan_id, str):
                _register_id(all_ids, plan_id, f"{label}:plan", issues)

        for session in day.get("work_sessions", []):
            _validate_reference(session, label, projects, milestones, tasks, issues)
            session_id = session.get("session_id")
            if isinstance(session_id, str):
                _register_id(all_ids, session_id, f"{label}:session", issues)
            if session.get("checked_out_at") is None:
                open_sessions.append((path, day, session))
            checked_out = session.get("checked_out_at")
            if checked_out:
                try:
                    if _iso(checked_out) < _iso(session["checked_in_at"]):
                        issues.append(Issue("error", label, f"Session {session_id} ends before it starts"))
                except (ValueError, KeyError):
                    pass

        for note in day.get("notes", []):
            note_id = note.get("note_id")
            if isinstance(note_id, str):
                _register_id(all_ids, note_id, f"{label}:note", issues)

        for todo in day.get("todolist", []):
            todo_id = todo.get("todo_id")
            if isinstance(todo_id, str):
                _register_id(all_ids, todo_id, f"{label}:todo", issues)

        for meal in day.get("meals", []):
            meal_id = meal.get("meal_id")
            if isinstance(meal_id, str):
                _register_id(all_ids, meal_id, f"{label}:meal", issues)

        for outing in day.get("outings", []):
            outing_id = outing.get("outing_id")
            if isinstance(outing_id, str):
                _register_id(all_ids, outing_id, f"{label}:outing", issues)

    if len(active_days) > 1:
        issues.append(Issue("error", "data/days", "More than one active life day exists"))
    if len(open_sessions) > 1:
        issues.append(Issue("error", "data/days", "More than one open work session exists"))

    _validate_index_file(paths, paths.current_index, "current-index.schema.json", issues)
    _validate_index_file(paths, paths.project_index, "project-index.schema.json", issues)
    _validate_index_file(paths, paths.calendar_index, "calendar-index.schema.json", issues)

    # medical validation
    if paths.medical_file.is_file():
        try:
            medical = read_json(paths.medical_file)
            issues.extend(schema_issues(paths, medical, "medical.schema.json", "data/medical.json"))
        except Exception as exc:
            issues.append(Issue("error", "data/medical.json", f"Cannot read JSON: {exc}"))

    # Pending validation
    if paths.pending_file.is_file():
        try:
            pending = read_json(paths.pending_file)
            issues.extend(schema_issues(paths, pending, "pending.schema.json", "data/pending.json"))
            for item in pending.get("items", []):
                pid = item.get("pending_id")
                if isinstance(pid, str):
                    _register_id(all_ids, pid, "data/pending.json:pending", issues)
        except Exception as exc:
            issues.append(Issue("error", "data/pending.json", f"Cannot read JSON: {exc}"))

    if paths.someday_file.is_file():
        try:
            someday = read_json(paths.someday_file)
            issues.extend(schema_issues(paths, someday, "someday.schema.json", "data/someday.json"))
            for item in someday.get("items", []):
                someday_id = item.get("someday_id")
                if isinstance(someday_id, str):
                    _register_id(all_ids, someday_id, "data/someday.json:someday", issues)
        except Exception as exc:
            issues.append(Issue("error", "data/someday.json", f"Cannot read JSON: {exc}"))

    # Private spark validation: keep diagnostics structural and avoid record details.
    spark_ids: dict[str, str] = {}
    for path in sorted(paths.private_spark.glob("*/*.json")):
        label = path.relative_to(paths.root).as_posix()
        try:
            store = read_json(path)
        except Exception as exc:
            issues.append(Issue("error", label, f"Cannot read JSON: {exc}"))
            continue
        issues.extend(schema_issues(paths, store, "private-spark.schema.json", label))
        try:
            datetime.strptime(path.stem, "%Y-%m")
        except ValueError:
            issues.append(Issue("error", label, "Private spark filename must be YYYY-MM.json"))
        if path.parent.name != path.stem[:4]:
            issues.append(Issue("error", label, "Private spark file path must be data/private/spark/YYYY/YYYY-MM.json"))
        for record in store.get("records", []):
            record_id = record.get("id")
            if isinstance(record_id, str):
                previous = spark_ids.get(record_id)
                if previous:
                    issues.append(Issue("error", label, f"Duplicate private spark id also used by {previous}"))
                else:
                    spark_ids[record_id] = label
            started_at = record.get("started_at")
            ended_at = record.get("ended_at")
            if started_at and ended_at:
                try:
                    if _iso(ended_at) < _iso(started_at):
                        issues.append(Issue("error", label, "Private spark record ends before it starts"))
                except ValueError:
                    pass
            primary = ended_at or started_at or record.get("created_at")
            if isinstance(primary, str):
                try:
                    if _iso(primary).astimezone(SEOUL).strftime("%Y-%m") != path.stem:
                        issues.append(Issue("error", label, "Private spark record is stored in the wrong month file"))
                except ValueError:
                    pass

    try:
        current = read_json(paths.current_index)
        expected_active = active_days[0] if active_days else None
        indexed = current.get("current_day")
        if expected_active is None and indexed is not None:
            issues.append(Issue("warning", "data/indexes/current.json", "Index points to a day but no active day exists"))
        elif expected_active is not None:
            expected_path, expected_day = expected_active
            if indexed is None or indexed.get("day_id") != expected_day.get("day_id"):
                issues.append(Issue("warning", "data/indexes/current.json", "Current day index is stale"))
        expected_session = open_sessions[0][2] if open_sessions else None
        indexed_session = current.get("current_work_session")
        if expected_session is None and indexed_session is not None:
            issues.append(Issue("warning", "data/indexes/current.json", "Index points to a closed work session"))
        elif expected_session is not None and (
            indexed_session is None or indexed_session.get("session_id") != expected_session.get("session_id")
        ):
            issues.append(Issue("warning", "data/indexes/current.json", "Current work session index is stale"))
    except Exception:
        pass

    try:
        calendar = read_json(paths.calendar_index)
        for key, event in calendar.get("events", {}).items():
            expected_key = f"{event.get('calendar_id')}::{event.get('event_id')}"
            if key != expected_key:
                issues.append(Issue("error", "data/indexes/calendar.json", f"Event key {key} does not match calendar/event ID"))
            links = event.get("links", {})
            project_id = links.get("project_id")
            milestone_id = links.get("milestone_id")
            task_id = links.get("task_id")
            day_id = links.get("day_id")
            if project_id and project_id not in projects:
                issues.append(Issue("warning", "data/indexes/calendar.json", f"Unknown project link {project_id}"))
            if milestone_id and milestone_id not in milestones:
                issues.append(Issue("warning", "data/indexes/calendar.json", f"Unknown milestone link {milestone_id}"))
            if task_id and task_id not in tasks:
                issues.append(Issue("warning", "data/indexes/calendar.json", f"Unknown task link {task_id}"))
            if day_id and day_id not in days:
                issues.append(Issue("warning", "data/indexes/calendar.json", f"Unknown day link {day_id}"))
    except Exception:
        pass

    return issues


def _register_id(registry: dict[str, str], value: str, location: str, issues: list[Issue]) -> None:
    previous = registry.get(value)
    if previous:
        issues.append(Issue("error", location, f"Duplicate UUID also used by {previous}"))
    else:
        registry[value] = location


def _register_calendar_link(registry: dict[str, str], value: str, location: str, issues: list[Issue]) -> None:
    previous = registry.get(value)
    if previous:
        issues.append(Issue("error", location, f"Calendar event ID is already linked by {previous}"))
    else:
        registry[value] = location


def _validate_reference(
    item: dict[str, Any],
    label: str,
    projects: dict[str, tuple[Path, dict[str, Any]]],
    milestones: dict[str, tuple[str, dict[str, Any]]],
    tasks: dict[str, tuple[str, str, dict[str, Any]]],
    issues: list[Issue],
) -> None:
    project_id = item.get("project_id")
    milestone_id = item.get("milestone_id")
    task_id = item.get("task_id")
    if project_id not in projects:
        issues.append(Issue("error", label, f"Unknown project reference {project_id}"))
    if milestone_id not in milestones:
        issues.append(Issue("error", label, f"Unknown milestone reference {milestone_id}"))
    elif milestones[milestone_id][0] != project_id:
        issues.append(Issue("error", label, "Milestone does not belong to referenced project"))
    if task_id not in tasks:
        issues.append(Issue("error", label, f"Unknown task reference {task_id}"))
    else:
        task_project, task_milestone, _ = tasks[task_id]
        if task_project != project_id or task_milestone != milestone_id:
            issues.append(Issue("error", label, "Task does not belong to referenced project and milestone"))


def _validate_index_file(paths: NeoPaths, path: Path, schema_name: str, issues: list[Issue]) -> None:
    label = path.relative_to(paths.root).as_posix()
    try:
        value = read_json(path)
        issues.extend(schema_issues(paths, value, schema_name, label))
    except Exception as exc:
        issues.append(Issue("error", label, f"Cannot read JSON: {exc}"))
