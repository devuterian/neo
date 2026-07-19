from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..errors import ConflictError, ValidationError
from ..utils import new_uuid, now_iso, parse_datetime
from .lifestyle import EXPECTED_MEDICATION_NAMES
from . import action_items


def create_day(wake_at: str | None = None) -> dict[str, Any]:
    wake = parse_datetime(wake_at)
    timestamp = wake.isoformat(timespec="seconds")
    return {
        "schema_version": 2,
        "day_id": new_uuid(),
        "date": wake.date().isoformat(),
        "status": "active",
        "wake_at": timestamp,
        "sleep_at": None,
        "closed_at": None,
        "workday_capacity": None,
        "external_schedule_snapshot": [],
        "work_plan": [],
        "todolist": [],
        "meals": [],
        "mood": None,
        "outings": [],
        "work_sessions": [],
        "calendar_work_event_ids": [],
        "notes": [],
        "medications": [],
        "showers": [],
        "hair_dries": [],
        "naps": [],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }


def close_day(day: dict[str, Any], closed_at: str | None = None) -> dict[str, Any]:
    result = deepcopy(day)
    if any(session["checked_out_at"] is None for session in result["work_sessions"]):
        raise ConflictError("Cannot close a life day with an open work session")
    result["status"] = "closed"
    result["closed_at"] = parse_datetime(closed_at).isoformat(timespec="seconds")
    result["updated_at"] = now_iso()
    return result


def void_day(day: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(day)
    if any(session["checked_out_at"] is None for session in result["work_sessions"]):
        raise ConflictError("Cannot void a life day with an open work session")
    result["status"] = "void"
    result["closed_at"] = now_iso()
    result["updated_at"] = now_iso()
    return result


def reopen_day(day: dict[str, Any]) -> dict[str, Any]:
    if day["status"] != "closed":
        raise ConflictError(f"Cannot reopen a life day in status {day['status']}")
    result = deepcopy(day)
    result["status"] = "active"
    result["closed_at"] = None
    result["updated_at"] = now_iso()
    return result


def set_capacity(day: dict[str, Any], value: float) -> dict[str, Any]:
    if value not in {0, 0.5, 1}:
        raise ValidationError("workday_capacity must be 0, 0.5, or 1")
    result = deepcopy(day)
    allocation = sum(item["planned_allocation"] for item in result["work_plan"])
    if allocation > value:
        raise ConflictError("Existing plan allocation exceeds the requested capacity")
    result["workday_capacity"] = value
    result["updated_at"] = now_iso()
    return result


def set_external_snapshot(day: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    result = deepcopy(day)
    result["external_schedule_snapshot"] = events
    result["updated_at"] = now_iso()
    return result


def plan_task(
    day: dict[str, Any],
    *,
    project: dict[str, Any],
    milestone: dict[str, Any],
    task: dict[str, Any],
    allocation: float,
    calendar_event_id: str | None = None,
) -> dict[str, Any]:
    if allocation not in {0.5, 1}:
        raise ValidationError("planned_allocation must be 0.5 or 1")
    if task["status"] not in {"todo", "in_progress"}:
        raise ConflictError(f"Cannot plan a task in status {task['status']}")
    result = deepcopy(day)
    if result["workday_capacity"] is None:
        raise ConflictError("Set workday_capacity before planning tasks")
    if result["workday_capacity"] == 0:
        raise ConflictError("Cannot plan project work on a capacity-0 day")
    if any(item["task_id"] == task["task_id"] for item in result["work_plan"]):
        raise ConflictError("Task is already planned for this life day")
    total = sum(item["planned_allocation"] for item in result["work_plan"]) + allocation
    if total > result["workday_capacity"]:
        raise ConflictError("Planned allocation exceeds workday_capacity")
    result["work_plan"].append(
        {
            "plan_item_id": new_uuid(),
            "project_id": project["project_id"],
            "project_title_snapshot": project["title"],
            "milestone_id": milestone["milestone_id"],
            "milestone_title_snapshot": milestone["title"],
            "task_id": task["task_id"],
            "task_title_snapshot": task["title"],
            "planned_allocation": allocation,
            "calendar_event_id": calendar_event_id,
            "created_at": now_iso(),
        }
    )
    if calendar_event_id and calendar_event_id not in result["calendar_work_event_ids"]:
        result["calendar_work_event_ids"].append(calendar_event_id)
    result["updated_at"] = now_iso()
    return result


def record_sleep(day: dict[str, Any], sleep_at: str | None = None) -> dict[str, Any]:
    result = deepcopy(day)
    result["sleep_at"] = parse_datetime(sleep_at).isoformat(timespec="seconds")
    result["updated_at"] = now_iso()
    return result


def clear_sleep(day: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(day)
    result["sleep_at"] = None
    result["updated_at"] = now_iso()
    return result


def add_nap(day: dict[str, Any], *, started_at: str | None = None) -> tuple[dict[str, Any], str]:
    result = deepcopy(day)
    if any(nap.get("ended_at") is None for nap in result.get("naps", [])):
        raise ConflictError("A nap is already open")
    started = parse_datetime(started_at).isoformat(timespec="seconds")
    nap_id = new_uuid()
    result.setdefault("naps", []).append(
        {"nap_id": nap_id, "started_at": started, "ended_at": None}
    )
    result["updated_at"] = now_iso()
    return result, nap_id


def finish_nap(day: dict[str, Any], nap_id: str, ended_at: str | None = None) -> dict[str, Any]:
    result = deepcopy(day)
    target = next((nap for nap in result.get("naps", []) if nap.get("nap_id") == nap_id), None)
    if target is None:
        raise ValidationError(f"Nap not found: {nap_id}")
    if target.get("ended_at") is not None:
        raise ConflictError("Nap is already closed")
    ended = parse_datetime(ended_at)
    started = parse_datetime(target["started_at"])
    if ended < started:
        raise ValidationError("Nap end cannot precede nap start")
    target["ended_at"] = ended.isoformat(timespec="seconds")
    result["updated_at"] = now_iso()
    return result


def update_nap(
    day: dict[str, Any],
    nap_id: str,
    *,
    started_at: str | None = None,
    ended_at: str | None = None,
) -> dict[str, Any]:
    if started_at is None and ended_at is None:
        raise ValidationError("At least one nap time is required")
    result = deepcopy(day)
    target = next((nap for nap in result.get("naps", []) if nap.get("nap_id") == nap_id), None)
    if target is None:
        raise ValidationError(f"Nap not found: {nap_id}")
    new_started = parse_datetime(started_at) if started_at is not None else parse_datetime(target["started_at"])
    new_ended = parse_datetime(ended_at) if ended_at is not None else (
        parse_datetime(target["ended_at"]) if target.get("ended_at") is not None else None
    )
    if new_ended is not None and new_ended < new_started:
        raise ValidationError("Nap end cannot precede nap start")
    target["started_at"] = new_started.isoformat(timespec="seconds")
    if ended_at is not None:
        assert new_ended is not None
        target["ended_at"] = new_ended.isoformat(timespec="seconds")
    result["updated_at"] = now_iso()
    return result


def remove_nap(day: dict[str, Any], nap_id: str) -> dict[str, Any]:
    result = deepcopy(day)
    before = len(result.get("naps", []))
    result["naps"] = [nap for nap in result.get("naps", []) if nap.get("nap_id") != nap_id]
    if len(result["naps"]) == before:
        raise ValidationError(f"Nap not found: {nap_id}")
    result["updated_at"] = now_iso()
    return result


def add_note(day: dict[str, Any], text: str) -> dict[str, Any]:
    result = deepcopy(day)
    result["notes"].append({"note_id": new_uuid(), "occurred_at": now_iso(), "text": text.strip()})
    result["updated_at"] = now_iso()
    return result


def add_todo(day: dict[str, Any], title: str, description: str = "") -> dict[str, Any]:
    result = deepcopy(day)
    store = action_items.add_item({"items": day["todolist"], "updated_at": day["updated_at"]}, title, description, id_key="todo_id")
    result["todolist"] = store["items"]
    result["updated_at"] = now_iso()
    return result


def set_todo_done(day: dict[str, Any], todo_id: str, done: bool) -> dict[str, Any]:
    result = deepcopy(day)
    store = action_items.set_done(
        {"items": day["todolist"], "updated_at": day["updated_at"]},
        todo_id,
        done,
        id_key="todo_id",
        entity_label="Todo",
    )
    result["todolist"] = store["items"]
    if result["todolist"] == day["todolist"]:
        return result
    result["updated_at"] = now_iso()
    return result


def remove_todo(day: dict[str, Any], todo_id: str) -> dict[str, Any]:
    result = deepcopy(day)
    store = action_items.remove_item(
        {"items": day["todolist"], "updated_at": day["updated_at"]},
        todo_id,
        id_key="todo_id",
        entity_label="Todo",
    )
    result["todolist"] = store["items"]
    result["updated_at"] = now_iso()
    return result


def check_in(
    day: dict[str, Any],
    *,
    project: dict[str, Any],
    milestone: dict[str, Any],
    task: dict[str, Any],
    at: str | None = None,
) -> tuple[dict[str, Any], str]:
    result = deepcopy(day)
    if any(session["checked_out_at"] is None for session in result["work_sessions"]):
        raise ConflictError("A work session is already open")
    session_id = new_uuid()
    result["work_sessions"].append(
        {
            "session_id": session_id,
            "project_id": project["project_id"],
            "project_title_snapshot": project["title"],
            "milestone_id": milestone["milestone_id"],
            "milestone_title_snapshot": milestone["title"],
            "task_id": task["task_id"],
            "task_title_snapshot": task["title"],
            "checked_in_at": parse_datetime(at).isoformat(timespec="seconds"),
            "checked_out_at": None,
            "note": None,
        }
    )
    result["updated_at"] = now_iso()
    return result, session_id


def check_out(day: dict[str, Any], session_id: str, at: str | None = None, note: str | None = None) -> dict[str, Any]:
    result = deepcopy(day)
    target = next((session for session in result["work_sessions"] if session["session_id"] == session_id), None)
    if target is None:
        raise ValidationError(f"Work session not found: {session_id}")
    if target["checked_out_at"] is not None:
        raise ConflictError("Work session is already closed")
    checked_out = parse_datetime(at)
    checked_in = parse_datetime(target["checked_in_at"])
    if checked_out < checked_in:
        raise ValidationError("Check-out time cannot precede check-in time")
    target["checked_out_at"] = checked_out.isoformat(timespec="seconds")
    target["note"] = note.strip() if note else None
    result["updated_at"] = now_iso()
    return result
