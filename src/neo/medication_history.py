from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from .errors import ValidationError
from .paths import NeoPaths
from .repository import Repository
from .transaction import read_json
from .utils import SEOUL, parse_datetime
from .validation import validate_document


def medication_history(
    paths: NeoPaths,
    *,
    name: str | None = None,
    action: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Read medication events across all life days without changing the workspace."""

    normalized_name = _normalize_name(name) if name is not None else None
    if action is not None and action not in {"taken", "skipped"}:
        raise ValidationError("medication action must be taken or skipped")
    since_date = _parse_date(since, "since") if since is not None else None
    until_date = _parse_date(until, "until") if until is not None else None
    if since_date and until_date and since_date > until_date:
        raise ValidationError("since date cannot be after until date")
    if limit is not None and limit <= 0:
        raise ValidationError("limit must be greater than zero")

    events: list[tuple[datetime | None, int, dict[str, Any]]] = []
    sequence = 0
    for day_path in Repository(paths).day_files():
        day = _read_v2_day(paths, day_path)
        life_day_date = day["date"]
        for medication in day["medications"]:
            event = _project_event(medication, life_day_date, day_path)
            if normalized_name is not None and _normalize_name(event["name"]) != normalized_name:
                continue
            if action is not None and event["action"] != action:
                continue
            if event["actual_date"] is not None:
                actual_date = date.fromisoformat(event["actual_date"])
                if since_date and actual_date < since_date:
                    continue
                if until_date and actual_date > until_date:
                    continue
            elif since_date or until_date:
                # An unknown actual date cannot be proven to match a date range.
                continue
            events.append((event["_occurred_datetime"], sequence, event))
            sequence += 1

    # Known actual times come first, newest first. Unknown times stay after them
    # and retain source order; recorded_at is deliberately not used as a fallback.
    events.sort(
        key=lambda item: (
            item[0] is not None,
            item[0] or datetime.min.replace(tzinfo=SEOUL),
            -item[1],
        ),
        reverse=True,
    )
    projected = []
    for _, _, event in events[:limit]:
        event.pop("_occurred_datetime", None)
        projected.append(event)
    return projected


def _read_v2_day(paths: NeoPaths, day_path: Path) -> dict[str, Any]:
    label = day_path.relative_to(paths.root).as_posix()
    try:
        day = read_json(day_path)
    except Exception as exc:
        raise ValidationError(f"Cannot read life day {label}: {exc}") from exc
    version = day.get("schema_version") if isinstance(day, dict) else None
    if version != 2:
        raise ValidationError(
            f"Unsupported life-day schema_version in {label}: {version}; "
            "medication history supports schema_version 2 only"
        )
    try:
        validate_document(paths, day, "day.schema.json", label)
    except (ValueError, KeyError, TypeError) as exc:
        raise ValidationError(f"Invalid life day {label}: {exc}") from exc
    return day


def _project_event(
    medication: dict[str, Any],
    life_day_date: str,
    day_path: Path,
) -> dict[str, Any]:
    occurred_at = medication["occurred_at"]
    occurred_datetime = None
    actual_date = None
    display_occurred_at = None
    if occurred_at is not None:
        try:
            occurred_datetime = parse_datetime(occurred_at)
        except ValidationError as exc:
            raise ValidationError(
                f"Invalid medication occurred_at in {day_path}: {exc}"
            ) from exc
        actual_date = occurred_datetime.astimezone(SEOUL).date().isoformat()
        display_occurred_at = occurred_datetime.isoformat(timespec="seconds")
    recorded_at = parse_datetime(medication["recorded_at"]).isoformat(timespec="seconds")
    return {
        "medication_id": medication["medication_id"],
        "name": medication["name"],
        "action": medication["action"],
        "occurred_at": display_occurred_at,
        "actual_date": actual_date,
        "recorded_at": recorded_at,
        "life_day_date": life_day_date,
        "dose": medication["dose"],
        "note": medication["note"],
        "_occurred_datetime": occurred_datetime,
    }


def _normalize_name(value: str) -> str:
    normalized = value.strip().casefold()
    if not normalized:
        raise ValidationError("medication name must not be empty")
    return normalized


def _parse_date(value: str, option: str) -> date:
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValidationError(f"{option} must be YYYY-MM-DD") from exc
