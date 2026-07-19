from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .domain import days as day_domain
from .errors import ApprovalRequiredError, AutoWakeRejectedError, ConflictError, NeoError, ValidationError
from .paths import NeoPaths
from .repository import Repository
from .transaction import read_json
from .validation import validate_all
from .workspace import commit_workspace


def resolve_day_or_auto_wake(
    repo: Repository,
    paths: NeoPaths,
    auto_wake_flag: str | None = None,
) -> tuple[Path, dict[str, Any]]:
    try:
        return repo.current_day_location()
    except NeoError:
        pass

    policy = auto_wake_flag or _load_auto_wake_policy(paths)
    if policy == "never":
        raise AutoWakeRejectedError(
            "No active life day exists and auto_wake is set to 'never'. "
            "Use 'neoctl day wake' to start one."
        )
    if policy == "ask":
        raise AutoWakeRejectedError(
            "No active life day exists. Hermes should ask the user whether to start one."
        )
    if policy == "always":
        new_day = day_domain.create_day(None)
        new_path = repo.day_path(new_day["date"])
        if new_path.exists():
            raise ConflictError(
                f"A life day already exists for wake date {new_day['date']}. "
                "Correct the existing record instead."
            )
        commit_workspace(paths, day_updates={new_path: new_day})
        return new_path, new_day
    raise ValidationError(f"Unknown auto_wake policy: {policy}")


def validation_result(paths: NeoPaths, action: str | None = None) -> dict[str, Any]:
    issues = validate_all(paths)
    errors = [issue for issue in issues if issue.severity == "error"]
    result = {
        "ok": not errors,
        "errors": [issue.as_dict() for issue in errors],
        "warnings": [issue.as_dict() for issue in issues if issue.severity == "warning"],
    }
    if action:
        result["action"] = action
    if errors:
        raise ValidationError("; ".join(f"{item.path}: {item.message}" for item in errors))
    return result


def require_approval(approved: bool, action: str) -> None:
    if not approved:
        raise ApprovalRequiredError(
            f"{action} requires explicit operator approval and --approve"
        )


def emit(value: Any, as_json: bool, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    if as_json or isinstance(value, (dict, list)):
        print(json.dumps(value, ensure_ascii=False, indent=2), file=stream)
    else:
        print(value, file=stream)


def relative(path: Path, paths: NeoPaths) -> str:
    return path.resolve().relative_to(paths.root.resolve()).as_posix()


def _load_auto_wake_policy(paths: NeoPaths) -> str:
    app_config = read_json(paths.root / "config" / "app.json")
    return app_config.get("auto_wake", "ask")
