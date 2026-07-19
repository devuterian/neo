from __future__ import annotations

import argparse
from typing import Any

from .cli_support import relative, require_approval
from .domain import projects as project_domain
from .errors import ConflictError, ValidationError
from .paths import NeoPaths
from .repository import Repository
from .transaction import read_json
from .utils import ensure_slug, slugify_ascii
from .workspace import commit_workspace


def handle_project(paths: NeoPaths, args: argparse.Namespace) -> Any:
    repo = Repository(paths)
    if args.project_command == "create":
        require_approval(args.approve, "project creation")
        slug = ensure_slug(args.slug) if args.slug else slugify_ascii(args.title)
        path = repo.project_path_for_slug(slug)
        if path.exists():
            raise ConflictError(f"Project slug already exists: {slug}")
        project = project_domain.create_project(args.title, slug, args.description)
        commit_workspace(paths, project_updates={path: project})
        return {"ok": True, "project_id": project["project_id"], "path": relative(path, paths)}
    if args.project_command == "list":
        return read_json(paths.project_index)
    if args.project_command == "show":
        return repo.resolve_project(args.project).data
    if args.project_command == "rename":
        require_approval(args.approve, "project rename")
        location = repo.resolve_project(args.project)
        new_title = args.title if args.title else location.data["title"]
        new_slug = ensure_slug(args.slug) if args.slug else location.data["slug"]
        if args.title is None and args.slug is None:
            raise ValidationError("At least one of --title or --slug is required")
        destination = repo.project_path_for_slug(new_slug)
        if destination != location.path and destination.exists():
            raise ConflictError(f"Project slug already exists: {new_slug}")
        updated = project_domain.rename_project(location.data, new_title, new_slug)
        deletes = {location.path} if destination != location.path else set()
        commit_workspace(paths, project_updates={destination: updated}, delete_paths=deletes)
        return {"ok": True, "project_id": updated["project_id"], "path": relative(destination, paths)}
    if args.project_command == "status":
        require_approval(args.approve, "project status change")
        location = repo.resolve_project(args.project)
        updated = project_domain.set_project_status(
            location.data,
            args.status,
            reason=args.reason,
            waiting_on=args.waiting_on,
            next_review_at=args.next_review_at,
            pause_reason=args.pause_reason,
            resume_condition=args.resume_condition,
        )
        commit_workspace(paths, project_updates={location.path: updated})
        return {"ok": True, "project_id": updated["project_id"], "status": updated["status"]}
    if args.project_command == "link-deadline":
        require_approval(args.approve, "deadline change")
        location = repo.resolve_project(args.project)
        updated = project_domain.link_deadline_calendar(location.data, args.event_id)
        commit_workspace(paths, project_updates={location.path: updated})
        return {"ok": True, "deadline_calendar_event_id": args.event_id}
    if args.project_command == "decision":
        require_approval(args.approve, "important project decision")
        location = repo.resolve_project(args.project)
        updated = project_domain.add_decision(location.data, args.title, args.detail)
        commit_workspace(paths, project_updates={location.path: updated})
        return {"ok": True, "project_id": updated["project_id"]}
    raise ValidationError("Unsupported project command")


def handle_milestone(paths: NeoPaths, args: argparse.Namespace) -> Any:
    repo = Repository(paths)
    location = repo.resolve_project(args.project)
    if args.milestone_command == "add":
        require_approval(args.approve, "milestone creation")
        updated, milestone_id = project_domain.add_milestone(
            location.data,
            args.title,
            args.remaining_effort,
        )
        commit_workspace(paths, project_updates={location.path: updated})
        return {"ok": True, "milestone_id": milestone_id}
    milestone = repo.resolve_milestone(location.data, args.milestone)
    if args.milestone_command == "status":
        require_approval(args.approve, "milestone status change")
        updated = project_domain.set_milestone_status(
            location.data,
            milestone["milestone_id"],
            args.status,
        )
        commit_workspace(paths, project_updates={location.path: updated})
        return {"ok": True, "milestone_id": milestone["milestone_id"], "status": args.status}
    if args.milestone_command == "effort":
        require_approval(args.approve, "remaining effort change")
        updated = project_domain.set_milestone_effort(
            location.data,
            milestone["milestone_id"],
            args.value,
        )
        commit_workspace(paths, project_updates={location.path: updated})
        return {
            "ok": True,
            "milestone_id": milestone["milestone_id"],
            "remaining_effort": args.value,
        }
    if args.milestone_command == "link-calendar":
        updated = project_domain.link_milestone_calendar(
            location.data,
            milestone["milestone_id"],
            args.event_id,
        )
        commit_workspace(paths, project_updates={location.path: updated})
        return {
            "ok": True,
            "milestone_id": milestone["milestone_id"],
            "calendar_event_id": args.event_id,
        }
    raise ValidationError("Unsupported milestone command")


def handle_task(paths: NeoPaths, args: argparse.Namespace) -> Any:
    repo = Repository(paths)
    if args.task_command == "list":
        locations = [repo.resolve_project(args.project)] if args.project else repo.load_projects()
        items = []
        for location in locations:
            for milestone in location.data["milestones"]:
                for task in milestone["tasks"]:
                    if args.status and task["status"] != args.status:
                        continue
                    items.append(
                        {
                            "project_id": location.data["project_id"],
                            "project_title": location.data["title"],
                            "milestone_id": milestone["milestone_id"],
                            "milestone_title": milestone["title"],
                            "task_id": task["task_id"],
                            "title": task["title"],
                            "status": task["status"],
                        }
                    )
        return {"tasks": items}
    if args.task_command == "add":
        location = repo.resolve_project(args.project)
        milestone = repo.resolve_milestone(location.data, args.milestone)
        updated, task_id = project_domain.add_task(
            location.data,
            milestone["milestone_id"],
            args.title,
        )
        commit_workspace(paths, project_updates={location.path: updated})
        return {"ok": True, "task_id": task_id}
    location = repo.resolve_task(args.task, args.project)
    if args.task_command == "status":
        updated = project_domain.set_task_status(
            location.project,
            location.task["task_id"],
            args.status,
            waiting_on=args.waiting_on,
        )
        commit_workspace(paths, project_updates={location.project_path: updated})
        return {"ok": True, "task_id": location.task["task_id"], "status": args.status}
    if args.task_command == "note":
        updated = project_domain.add_task_note(
            location.project,
            location.task["task_id"],
            args.text,
        )
        commit_workspace(paths, project_updates={location.project_path: updated})
        return {"ok": True, "task_id": location.task["task_id"]}
    raise ValidationError("Unsupported task command")
