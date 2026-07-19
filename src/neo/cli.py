from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from .cli_days import handle_day, handle_work
from .cli_operations import (
    _parse_last_days,
    handle_calendar,
    handle_doctor,
    handle_fridge,
    handle_medical,
    handle_message,
    handle_pending,
    handle_private,
    handle_someday,
)
from .cli_parser import build_parser
from .cli_projects import handle_milestone, handle_project, handle_task
from .cli_resources import handle_resource
from .cli_support import (
    emit,
    relative,
    require_approval,
    resolve_day_or_auto_wake,
    validation_result,
)
from .errors import NeoError, ValidationError
from .migrate import migrate_state
from .initialize import initialize_workspace
from .paths import NeoPaths
from .workspace import rebuild_derived


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            initialize_workspace(__import__("pathlib").Path.cwd())
        paths = NeoPaths.discover()
        result = dispatch(paths, args)
        emit(result, args.json)
        return 0
    except (NeoError, ValueError, OSError, json.JSONDecodeError) as exc:
        emit(
            {"ok": False, "error": str(exc)},
            getattr(args, "json", False),
            error=True,
        )
        return 2


def console_main() -> None:
    """Console entry point with deterministic process termination."""

    code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


def dispatch(paths: NeoPaths, args: argparse.Namespace) -> Any:
    if args.command == "init":
        rebuild_derived(paths)
        return validation_result(paths, action="initialized")
    if args.command == "validate":
        return validation_result(paths)
    if args.command == "migrate":
        return migrate_state(paths)
    if args.command == "doctor":
        return handle_doctor(paths)
    if args.command == "message":
        return handle_message(paths, args)
    if args.command in {"index", "brief"}:
        rebuild_derived(paths)
        return {"ok": True, "action": "derived files rebuilt"}
    if args.command == "resource":
        return handle_resource(paths, args)
    if args.command == "project":
        return handle_project(paths, args)
    if args.command == "milestone":
        return handle_milestone(paths, args)
    if args.command == "task":
        return handle_task(paths, args)
    if args.command == "day":
        return handle_day(paths, args)
    if args.command == "work":
        return handle_work(paths, args)
    if args.command == "calendar":
        return handle_calendar(paths, args)
    if args.command == "medical":
        return handle_medical(paths, args)
    if args.command == "pending":
        return handle_pending(paths, args)
    if args.command == "someday":
        return handle_someday(paths, args)
    if args.command == "fridge":
        return handle_fridge(paths, args)
    if args.command == "private":
        return handle_private(paths, args)
    raise ValidationError("Unsupported command")


if __name__ == "__main__":
    console_main()
