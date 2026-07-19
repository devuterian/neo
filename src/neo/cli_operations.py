from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .cli_support import relative, require_approval
from .domain import calendar as calendar_domain
from .domain import fridge as fridge_domain
from .domain import medical as medical_domain
from .domain import pending as pending_domain
from .domain import someday as someday_domain
from .domain import private_spark as spark_domain
from .errors import NeoError, NotFoundError, ValidationError
from .paths import NeoPaths
from .repository import Repository
from .transaction import read_json, repository_lock, write_batch
from .utils import now_iso, parse_datetime, today_seoul
from .validation import validate_all, validate_document
from .workspace import _git_commit, commit_workspace


def handle_calendar(paths: NeoPaths, args: argparse.Namespace) -> Any:
    if args.calendar_command == "show":
        return read_json(paths.calendar_index)
    if args.calendar_command == "import-index":
        payload = read_json(args.input)
        normalized = calendar_domain.normalize_calendar_index(payload)
        validate_document(
            paths,
            normalized,
            "calendar-index.schema.json",
            str(args.input),
        )
        commit_workspace(paths, calendar_update=normalized)
        return {
            "ok": True,
            "events": len(normalized["events"]),
            "fetched_at": normalized["source"]["fetched_at"],
        }
    if args.calendar_command == "refresh":
        build_script = paths.root / "scripts" / "build_calendar_index.py"
        output_path = Path("/tmp/neo-calendar-index.json")
        result = subprocess.run(
            [
                sys.executable,
                str(build_script),
                "--range-weeks",
                str(args.range_weeks),
                "--output",
                str(output_path),
            ],
            cwd=paths.root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise NeoError(f"Calendar refresh failed: {result.stderr.strip()}")
        payload = read_json(output_path)
        normalized = calendar_domain.normalize_calendar_index(payload)
        validate_document(
            paths,
            normalized,
            "calendar-index.schema.json",
            str(output_path),
        )
        commit_workspace(paths, calendar_update=normalized)
        return {
            "ok": True,
            "events": len(normalized["events"]),
            "fetched_at": normalized["source"]["fetched_at"],
        }
    if args.calendar_command == "mark-unavailable":
        current = read_json(paths.calendar_index)
        current["generated_at"] = now_iso()
        current["source"]["status"] = "unavailable"
        current["source"]["error"] = args.error
        commit_workspace(paths, calendar_update=current)
        return {"ok": True, "status": "unavailable"}
    raise ValidationError("Unsupported calendar command")


def handle_medical(paths: NeoPaths, args: argparse.Namespace) -> Any:
    store = read_json(paths.medical_file) if paths.medical_file.is_file() else medical_domain.empty_store()
    if args.medical_command == "list":
        return medical_domain.with_status(store)
    if args.medical_command == "add":
        updated, medical_id = medical_domain.add_record(
            store, provider=args.provider, title=args.title, last_date=args.at,
            cycle_days=args.cycle_days, kind=args.kind, note=args.note,
        )
        commit_workspace(paths, medical_update=updated)
        return {"ok": True, "medical_id": medical_id}
    if args.medical_command == "record":
        updated = medical_domain.record_event(store, args.medical_id, at=args.at or today_seoul().isoformat(), note=args.note)
        commit_workspace(paths, medical_update=updated)
        return {"ok": True, "medical_id": args.medical_id, "last_date": args.at or today_seoul().isoformat()}
    if args.medical_command == "remove":
        require_approval(args.approve, "medical record removal")
        updated = medical_domain.remove_record(store, args.medical_id)
        commit_workspace(paths, medical_update=updated)
        return {"ok": True, "medical_id": args.medical_id, "removed": True}
    raise ValidationError("Unsupported medical command")


def handle_pending(paths: NeoPaths, args: argparse.Namespace) -> Any:
    if args.pending_command == "list":
        if not paths.pending_file.is_file():
            return {"items": []}
        return read_json(paths.pending_file)
    if args.pending_command == "add":
        pending = (
            read_json(paths.pending_file)
            if paths.pending_file.is_file()
            else pending_domain.create_pending()
        )
        updated = pending_domain.add_pending_item(
            pending,
            args.title,
            args.description,
            carried_from_day_id=args.carried_from,
        )
        commit_workspace(paths, pending_update=updated)
        return {"ok": True}
    if paths.pending_file.is_file():
        pending = read_json(paths.pending_file)
    else:
        raise NotFoundError("No pending items. Use 'neoctl pending add' to create one.")
    if args.pending_command == "done":
        updated = pending_domain.set_pending_done(pending, args.pending, True)
    elif args.pending_command == "undo":
        updated = pending_domain.set_pending_done(pending, args.pending, False)
    elif args.pending_command == "remove":
        updated = pending_domain.remove_pending_item(pending, args.pending)
    else:
        raise ValidationError("Unsupported pending command")
    commit_workspace(paths, pending_update=updated)
    return {"ok": True}


def handle_someday(paths: NeoPaths, args: argparse.Namespace) -> Any:
    if args.someday_command == "list":
        store = read_json(paths.someday_file) if paths.someday_file.is_file() else someday_domain.create_someday()
        items = store["items"] if args.all else [item for item in store["items"] if not item["done"]]
        return {"items": items, "count": len(items)}
    if args.someday_command == "add":
        store = read_json(paths.someday_file) if paths.someday_file.is_file() else someday_domain.create_someday()
        updated = someday_domain.add_someday_item(store, args.title, args.description)
        commit_workspace(paths, someday_update=updated)
        return {"ok": True}
    if not paths.someday_file.is_file():
        raise NotFoundError("No someday items. Use 'neoctl someday add' to create one.")
    store = read_json(paths.someday_file)
    if args.someday_command == "done":
        updated = someday_domain.set_someday_done(store, args.someday, True)
    elif args.someday_command == "undo":
        updated = someday_domain.set_someday_done(store, args.someday, False)
    elif args.someday_command == "remove":
        updated = someday_domain.remove_someday_item(store, args.someday)
    else:
        raise ValidationError("Unsupported someday command")
    commit_workspace(paths, someday_update=updated)
    return {"ok": True}


def handle_fridge(paths: NeoPaths, args: argparse.Namespace) -> Any:
    def load_fridge() -> dict[str, Any]:
        if paths.fridge_file.is_file():
            return read_json(paths.fridge_file)
        return fridge_domain.create_fridge()

    if args.fridge_command == "list":
        fridge = load_fridge()
        if args.all:
            items = fridge_domain.list_all(fridge)
        else:
            items = fridge_domain.list_available(
                fridge,
                location=args.location,
                category=args.category,
            )
        return {"items": items, "count": len(items)}

    if args.fridge_command == "expired":
        fridge = load_fridge()
        today = today_seoul().isoformat()
        available = fridge_domain.list_available(fridge)
        expired = [
            item
            for item in available
            if item.get("expires_at") and item["expires_at"] <= today
        ]
        return {"items": expired, "count": len(expired)}

    if args.fridge_command == "add":
        fridge = load_fridge()
        updated = fridge_domain.add_item(
            fridge,
            args.name,
            category=args.category,
            quantity=args.quantity,
            location=args.location,
            expires_at=args.expires,
            notes=args.notes,
            source=args.source,
            ordered_at=args.ordered_at,
            expected_at=args.expected_at,
        )
        commit_workspace(paths, fridge_update=updated)
        return {"ok": True}

    if args.fridge_command == "transit":
        fridge = load_fridge()
        items = fridge_domain.list_in_transit(fridge)
        return {"items": items, "count": len(items)}

    fridge = load_fridge()
    if args.fridge_command == "arrive":
        if args.all:
            updated = fridge_domain.arrive_all_transit(
                fridge,
                location=args.location,
            )
        elif args.item_id:
            updated = fridge_domain.arrive_item(
                fridge,
                args.item_id,
                location=args.location,
            )
        else:
            raise ValidationError("Specify item_id or --all")
    elif args.fridge_command == "consume":
        updated = fridge_domain.consume_item(
            fridge,
            args.item_id,
            quantity=args.quantity,
        )
    elif args.fridge_command == "remove":
        updated = fridge_domain.remove_item(fridge, args.item_id)
    else:
        raise ValidationError("Unsupported fridge command")
    commit_workspace(paths, fridge_update=updated)
    return {"ok": True}


def handle_private(paths: NeoPaths, args: argparse.Namespace) -> Any:
    if args.private_command != "spark":
        raise ValidationError("Unsupported private command")

    if args.spark_command == "log":
        life_day = args.life_day
        if life_day is None:
            try:
                _, day = Repository(paths).current_day_location()
                life_day = day["date"]
            except NeoError:
                if args.ended_at:
                    life_day = parse_datetime(args.ended_at).date().isoformat()
                else:
                    raise ValidationError(
                        "--life-day is required when no active life day exists"
                    )
        record = spark_domain.make_record(
            kind=args.kind,
            life_day=life_day,
            partner=args.partner,
            started_at=args.started_at,
            ended_at=args.ended_at,
            mood=args.mood,
            condition=args.condition,
            discomfort=args.discomfort,
            note=args.note,
            allow_imprecise=args.allow_imprecise,
        )
        path, saved = spark_domain.log_record(paths, record)
        return {"ok": True, "id": saved["id"], "path": relative(path, paths)}

    if args.spark_command == "list":
        last_days = _parse_last_days(args.last)
        records = spark_domain.list_records(
            paths,
            month=args.month,
            life_day=args.life_day,
            last_days=last_days,
            include_notes=args.include_notes,
        )
        return {"records": records, "count": len(records)}

    if args.spark_command == "edit":
        changes = {
            "kind": args.kind,
            "partner": args.partner,
            "started_at": args.started_at,
            "ended_at": args.ended_at,
            "mood": args.mood,
            "condition": args.condition,
            "discomfort": args.discomfort,
            "note": args.note,
        }
        if all(value is None for value in changes.values()):
            raise ValidationError("At least one field must be provided")
        record = spark_domain.edit_record(paths, args.record_id, changes)
        return {"ok": True, "record": record}

    if args.spark_command == "remove":
        require_approval(args.approve, "private spark removal")
        return spark_domain.remove_record(paths, args.record_id)

    if args.spark_command == "report":
        last_days = _parse_last_days(args.last)
        markdown = spark_domain.build_report(
            paths,
            month=args.month,
            life_day=args.life_day,
            last_days=last_days,
            include_notes=args.include_notes,
        )
        if args.output:
            output = args.output
        else:
            suffix = (
                args.month
                or args.life_day
                or (f"last-{last_days}d" if last_days else "all")
            )
            output = Path("/tmp") / f"spark-{suffix}.md"
        spark_domain.write_report(markdown, output)
        return {"ok": True, "path": str(output), "committed": False}

    raise ValidationError("Unsupported private spark command")


def handle_message(paths: NeoPaths, args: argparse.Namespace) -> Any:
    if args.message_command != "log":
        raise ValidationError("Unsupported message command")
    dt = parse_datetime(args.at)
    path = paths.root / "data" / "message-log" / f"{dt.date().isoformat()}.jsonl"
    line = (
        json.dumps(
            {
                "timestamp": dt.isoformat(timespec="seconds"),
                "role": args.role,
                "content": args.content,
            },
            ensure_ascii=False,
        )
        + "\n"
    )
    with repository_lock(paths):
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        write_batch(paths, {}, {path: existing + line})
        _git_commit(paths, [path], set())
    return {"ok": True, "path": str(path.relative_to(paths.root))}


def handle_doctor(paths: NeoPaths) -> Any:
    issues = validate_all(paths)
    repo = Repository(paths)
    try:
        _, day = repo.current_day_location()
        active_day = day.get("day_id")
        sessions = [
            session
            for session in day.get("work_sessions", [])
            if session.get("checked_out_at") is None
        ]
        active_session = sessions[0]["session_id"] if sessions else None
    except Exception:
        active_day = None
        active_session = None
    projects = [location.data for location in repo.load_projects()]
    open_projects = sum(
        1
        for project in projects
        if project.get("status") not in {"done", "cancelled"}
    )
    calendar = read_json(paths.calendar_index) if paths.calendar_index.is_file() else {}
    git = subprocess.run(
        ["git", "status", "--short"],
        cwd=paths.root,
        capture_output=True,
        text=True,
    )
    last_push = read_json(paths.last_push) if paths.last_push.is_file() else None
    try:
        spark = spark_domain.doctor_summary(paths)
    except Exception as exc:
        spark = {"status": "unavailable", "error": str(exc)}
    migration_needed = []
    for day_file in paths.days.glob("*/*.json"):
        try:
            if "medications" not in read_json(day_file):
                migration_needed.append(str(day_file.relative_to(paths.root)))
        except Exception:
            pass
    has_errors = any(issue.severity == "error" for issue in issues)
    return {
        "ok": not has_errors,
        "validate": "failed" if has_errors else "ok",
        "active_day_id": active_day,
        "active_work_session_id": active_session,
        "open_projects": open_projects,
        "calendar": {
            "status": calendar.get("source", {}).get("status"),
            "generated_at": calendar.get("generated_at"),
        },
        "private_spark": spark,
        "git_status": git.stdout.strip() or "clean",
        "last_push": last_push,
        "migration_needed": migration_needed,
        "issues": [issue.__dict__ for issue in issues[:10]],
    }


def _parse_last_days(value: str | None) -> int | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized.endswith("d"):
        normalized = normalized[:-1]
    try:
        days = int(normalized)
    except ValueError as exc:
        raise ValidationError("--last must look like Nd, for example 7d") from exc
    if days <= 0:
        raise ValidationError("--last must be positive")
    return days
