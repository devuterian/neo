from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .cli_support import require_approval, resolve_day_or_auto_wake
from .domain import days as day_domain
from .domain import lifestyle
from .domain import projects as project_domain
from .errors import ConflictError, NeoError, NotFoundError, ValidationError
from .paths import NeoPaths
from .repository import Repository
from .transaction import read_json
from .workspace import commit_workspace
from .mutations import MutationService
from .medication_history import medication_history


def handle_day(paths: NeoPaths, args: argparse.Namespace) -> Any:
    repo = Repository(paths)
    if args.day_command == "correct":
        if not getattr(args, "date", None):
            raise ValidationError("day correct requires --date")
        return MutationService(paths).mutate(
            "correct", "day", args.date, field=args.field, value=args.value,
            reason=args.reason, expected_revision=args.expected_revision,
        )
    if args.day_command == "wake":
        new_day = day_domain.create_day(args.at)
        new_path = repo.day_path(new_day["date"])
        if new_path.exists():
            raise ConflictError(
                f"A life day already exists for wake date {new_day['date']}. "
                "Correct the existing record instead."
            )
        updates: dict[Path, dict[str, Any]] = {new_path: new_day}
        try:
            old_path, old_day = repo.current_day_location()
            updates[old_path] = day_domain.close_day(old_day, new_day["wake_at"])
        except NeoError as exc:
            if "No active life day" not in str(exc):
                raise
        commit_workspace(paths, day_updates=updates)
        return {"ok": True, "day_id": new_day["day_id"], "date": new_day["date"]}
    if args.day_command == "reopen":
        require_approval(args.approve, "life-day reopen")
        closed_days: list[tuple[Path, dict[str, Any]]] = []
        for day_file in repo.day_files():
            day_data = read_json(day_file)
            if day_data["status"] == "closed":
                closed_days.append((day_file, day_data))
        if not closed_days:
            raise NotFoundError("No closed life day to reopen")
        closed_days.sort(key=lambda item: item[1]["date"], reverse=True)
        day_path, day = closed_days[0]
        updated = day_domain.reopen_day(day)
        commit_workspace(paths, day_updates={day_path: updated})
        return {
            "ok": True,
            "day_id": updated["day_id"],
            "date": updated["date"],
            "status": updated["status"],
        }

    if args.day_command == "med" and args.med_command == "history":
        return {
            "ok": True,
            "medications": medication_history(
                paths,
                name=args.name,
                action=args.action,
                since=args.since,
                until=args.until,
                limit=args.limit,
            ),
        }

    if getattr(args, "date", None):
        day_path, day = repo.day_location_by_date(args.date)
    else:
        day_path, day = resolve_day_or_auto_wake(
            repo,
            paths,
            getattr(args, "auto_wake", None),
        )

    if args.day_command == "capacity":
        updated = day_domain.set_capacity(day, args.value)
    elif args.day_command == "work-plan-task":
        task_location = repo.resolve_task(args.task, args.project)
        updated = day_domain.plan_task(
            day,
            project=task_location.project,
            milestone=task_location.milestone,
            task=task_location.task,
            allocation=args.allocation,
            calendar_event_id=args.calendar_event_id,
        )
    elif args.day_command == "snapshot-calendar":
        calendar = read_json(paths.calendar_index)
        events = []
        for event_id in args.event_id:
            event = calendar["events"].get(event_id)
            if event is None:
                raise ValidationError(
                    f"Calendar event is not in the current index: {event_id}"
                )
            events.append(
                {
                    "event_id": event["event_id"],
                    "calendar_id": event["calendar_id"],
                    "title": event["title"],
                    "starts_at": event["starts_at"],
                    "ends_at": event["ends_at"],
                    "all_day": event["all_day"],
                }
            )
        updated = day_domain.set_external_snapshot(day, events)
    elif args.day_command == "sleep":
        updated = (
            day_domain.clear_sleep(day)
            if args.clear
            else day_domain.record_sleep(day, args.at)
        )
    elif args.day_command == "nap":
        if args.nap_command == "go":
            updated, nap_id = day_domain.add_nap(day, started_at=args.at)
            commit_workspace(paths, day_updates={day_path: updated})
            return {"ok": True, "day_id": updated["day_id"], "nap_id": nap_id}
        if args.nap_command == "back":
            open_nap = next((nap for nap in day.get("naps", []) if nap.get("nap_id") == args.nap), None)
            if open_nap is None:
                raise ValidationError(f"Nap not found: {args.nap}")
            updated = day_domain.finish_nap(day, args.nap, args.at)
        elif args.nap_command == "remove":
            updated = day_domain.remove_nap(day, args.nap)
        elif args.nap_command == "edit":
            updated = day_domain.update_nap(
                day,
                args.nap,
                started_at=args.started_at,
                ended_at=args.ended_at,
            )
        else:
            raise ValidationError("Unsupported nap command")
    elif args.day_command == "note":
        updated = day_domain.add_note(day, args.text)
    elif args.day_command == "void":
        require_approval(args.approve, "life-day void")
        updated = day_domain.void_day(day)
    elif args.day_command == "todo":
        if args.todo_command == "add":
            updated = day_domain.add_todo(day, args.title, args.description)
        elif args.todo_command == "done":
            updated = day_domain.set_todo_done(day, args.todo, True)
        elif args.todo_command == "undo":
            updated = day_domain.set_todo_done(day, args.todo, False)
        elif args.todo_command == "remove":
            updated = day_domain.remove_todo(day, args.todo)
        else:
            raise ValidationError("Unsupported todo command")
    elif args.day_command == "meal":
        if args.meal_command == "add":
            updated = lifestyle.add_meal(
                day,
                tag=args.tag,
                what=args.what,
                at=args.at,
            )
        elif args.meal_command == "remove":
            updated = lifestyle.remove_meal(day, args.meal)
        else:
            raise ValidationError("Unsupported meal command")
    elif args.day_command == "mood":
        if args.mood_command == "set":
            updated = lifestyle.set_mood(day, args.summary, args.reason)
        elif args.mood_command == "clear":
            updated = lifestyle.clear_mood(day)
        else:
            raise ValidationError("Unsupported mood command")
    elif args.day_command == "outing":
        if args.outing_command == "go":
            updated = lifestyle.add_outing(
                day,
                left_at=args.at,
                place=args.place,
                purpose=args.purpose,
            )
        elif args.outing_command == "back":
            updated = lifestyle.return_from_outing(day, args.outing, args.at)
        elif args.outing_command == "remove":
            updated = lifestyle.remove_outing(day, args.outing)
        else:
            raise ValidationError("Unsupported outing command")
    elif args.day_command == "med":
        if args.med_command == "take":
            updated, medication_id = lifestyle.add_medication_event(
                day,
                name=args.name,
                action="taken",
                occurred_at=args.at,
                dose=args.dose,
                note=args.note,
            )
            commit_workspace(paths, day_updates={day_path: updated})
            return {"ok": True, "day_id": updated["day_id"], "medication_id": medication_id}
        elif args.med_command == "skip":
            updated, medication_id = lifestyle.add_medication_event(
                day,
                name=args.name,
                action="skipped",
                occurred_at=args.at,
                note=args.reason,
            )
            commit_workspace(paths, day_updates={day_path: updated})
            return {"ok": True, "day_id": updated["day_id"], "medication_id": medication_id}
        elif args.med_command == "remove":
            updated = lifestyle.remove_medication_event(day, args.medication_id)
            commit_workspace(paths, day_updates={day_path: updated})
            return {"ok": True, "removed": args.medication_id}
        elif args.med_command == "status":
            status = lifestyle.medication_status(day)
            return {"ok": True, "medications": day.get("medications", []), "summary": status}
        else:
            raise ValidationError("Unsupported med command")
    elif args.day_command == "shower":
        if args.shower_command == "go":
            updated = lifestyle.add_shower(
                day,
                started_at=args.at,
                shower_type=args.type,
            )
        elif args.shower_command == "back":
            updated = lifestyle.finish_shower(day, args.shower, args.at)
        elif args.shower_command == "remove":
            updated = lifestyle.remove_shower(day, args.shower)
        else:
            raise ValidationError("Unsupported shower command")
    elif args.day_command == "hair-dry":
        if args.hair_dry_command == "go":
            updated = lifestyle.add_hair_dry(day, started_at=args.at)
        elif args.hair_dry_command == "back":
            updated = lifestyle.finish_hair_dry(day, args.hair_dry, args.at)
        elif args.hair_dry_command == "remove":
            updated = lifestyle.remove_hair_dry(day, args.hair_dry)
        else:
            raise ValidationError("Unsupported hair-dry command")
    else:
        raise ValidationError("Unsupported day command")

    commit_workspace(paths, day_updates={day_path: updated})
    return {"ok": True, "day_id": updated["day_id"], "status": updated["status"]}



def handle_work(paths: NeoPaths, args: argparse.Namespace) -> Any:
    repo = Repository(paths)
    if args.work_command == "check-in":
        day_path, day = resolve_day_or_auto_wake(
            repo,
            paths,
            getattr(args, "auto_wake", None),
        )
        location = repo.resolve_task(args.task, args.project)
        if location.task["status"] in {"done", "cancelled", "waiting"}:
            raise ConflictError(
                f"Task cannot be checked in from status {location.task['status']}"
            )
        updated_day, session_id = day_domain.check_in(
            day,
            project=location.project,
            milestone=location.milestone,
            task=location.task,
            at=args.at,
        )
        updated_project = project_domain.set_task_status(
            location.project,
            location.task["task_id"],
            "in_progress",
        )
        commit_workspace(
            paths,
            project_updates={location.project_path: updated_project},
            day_updates={day_path: updated_day},
        )
        return {
            "ok": True,
            "session_id": session_id,
            "task_id": location.task["task_id"],
        }
    if args.work_command == "check-out":
        day_path, day, session = repo.open_session()
        updated_day = day_domain.check_out(
            day,
            session["session_id"],
            args.at,
            args.note,
        )
        project_updates = {}
        if args.task_status:
            location = repo.resolve_task(session["task_id"])
            updated_project = project_domain.set_task_status(
                location.project,
                location.task["task_id"],
                args.task_status,
                waiting_on=args.waiting_on,
            )
            project_updates[location.project_path] = updated_project
        commit_workspace(
            paths,
            project_updates=project_updates,
            day_updates={day_path: updated_day},
        )
        return {
            "ok": True,
            "session_id": session["session_id"],
            "task_id": session["task_id"],
            "remaining_effort_review": (
                "Hermes should propose a milestone effort update for operator approval."
            ),
        }
    raise ValidationError("Unsupported work command")
