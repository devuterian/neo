from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .paths import NeoPaths
from .repository import Repository
from .transaction import read_json
from .utils import now_iso, relative_posix


def build_indexes(paths: NeoPaths) -> tuple[dict[str, Any], dict[str, Any]]:
    repo = Repository(paths)
    project_docs = [(location.path, location.data) for location in repo.load_projects()]
    day_docs = [(path, read_json(path)) for path in repo.day_files()]
    return build_indexes_from_documents(paths, project_docs, day_docs)


def build_indexes_from_documents(
    paths: NeoPaths,
    project_docs: Iterable[tuple[Path, dict[str, Any]]],
    day_docs: Iterable[tuple[Path, dict[str, Any]]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    generated_at = now_iso()
    project_docs = list(project_docs)
    day_docs = list(day_docs)
    active_days = [(path, day) for path, day in day_docs if day["status"] == "active"]
    open_sessions = [
        (day, session)
        for _, day in day_docs
        for session in day["work_sessions"]
        if session["checked_out_at"] is None
    ]

    current_day = None
    if active_days:
        path, day = active_days[0]
        current_day = {
            "day_id": day["day_id"],
            "date": day["date"],
            "path": relative_posix(path, paths.root),
        }

    current_session = None
    if open_sessions:
        day, session = open_sessions[0]
        current_session = {
            "session_id": session["session_id"],
            "day_id": day["day_id"],
            "task_id": session["task_id"],
        }

    current_index = {
        "schema_version": 1,
        "generated_at": generated_at,
        "current_day": current_day,
        "current_work_session": current_session,
    }

    project_entries = []
    for path, project in project_docs:
        open_task_count = sum(
            1
            for milestone in project["milestones"]
            for task in milestone["tasks"]
            if task["status"] not in {"done", "cancelled"}
        )
        project_entries.append(
            {
                "project_id": project["project_id"],
                "title": project["title"],
                "slug": project["slug"],
                "status": project["status"],
                "path": relative_posix(path, paths.root),
                "current_milestone_id": project["current_milestone_id"],
                "open_task_count": open_task_count,
                "updated_at": project["updated_at"],
            }
        )
    project_entries.sort(key=lambda item: (status_order(item["status"]), item["title"].casefold()))
    project_index = {
        "schema_version": 1,
        "generated_at": generated_at,
        "projects": project_entries,
    }
    return current_index, project_index


def status_order(status: str) -> int:
    order = {
        "active": 0,
        "waiting": 1,
        "paused": 2,
        "draft": 3,
        "complete": 4,
        "cancelled": 5,
    }
    return order.get(status, 99)
