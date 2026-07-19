from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .domain.fridge import CATEGORIES
from .domain.lifestyle import EXPECTED_MEDICATION_NAMES
from .utils import new_uuid5, now_iso

JsonDocument = dict[str, Any]

CATEGORY_MAP = {
    "protein": "ingredient",
    "produce": "ingredient",
    "condiment": "sauce",
    "beverage": "drink",
}

# Sentinel: a legacy false placeholder (no meaningful note) — skip during migration.
_PLACEHOLDER_NOTE_VALUES = {"", None, "건너뜀"}


def _is_placeholder(item: dict[str, Any]) -> bool:
    """Legacy placeholder: taken=false with no meaningful note."""
    if item.get("taken") is not False:
        return False
    note = item.get("note")
    if note is None:
        return True  # None note on taken=false is always a placeholder
    note = str(note).strip()
    return note in _PLACEHOLDER_NOTE_VALUES


def _migrate_medication_id(
    day_id: str,
    index: int,
    name: str,
    action: str,
    taken_at: str | None,
) -> str:
    """Deterministic UUID5 for legacy medication migration."""
    namespace = f"{day_id}:{index}:{name}:{action}:{taken_at or ''}"
    return new_uuid5(namespace)


@dataclass(frozen=True, slots=True)
class MigrationResult:
    document: JsonDocument
    changed: bool


def migrate_day_document(
    day: Mapping[str, Any],
    *,
    timestamp: str,
) -> MigrationResult:
    schema_version = day.get("schema_version",
        _infer_schema_version(day))

    if schema_version == 2:
        return MigrationResult(dict(day), False)
    if schema_version != 1:
        raise ValueError(
            f"Cannot migrate day from unknown schema_version {schema_version}"
        )

    updated = dict(day)
    updated["schema_version"] = 2

    legacy_meds = list(day.get("medications", []))
    new_meds: list[dict[str, Any]] = []
    day_id = str(day.get("day_id", ""))
    updated_at = str(day.get("updated_at", timestamp))

    for idx, item in enumerate(legacy_meds):
        name = str(item.get("name", "")).strip()
        if not name:
            raise ValueError(
                f"Cannot migrate legacy medication item {idx}: name is empty"
            )

        taken_val = item.get("taken")
        if not isinstance(taken_val, bool):
            raise ValueError(
                f"Cannot migrate legacy medication item {idx}: "
                f"taken must be boolean, got {type(taken_val).__name__}"
            )

        if taken_val is True:
            # A: taken=true → action=taken
            taken_at = item.get("taken_at")
            if taken_at is not None:
                taken_at = str(taken_at)
            note = item.get("note")
            note = str(note).strip() if note else None

            new_meds.append({
                "medication_id": _migrate_medication_id(
                    day_id, idx, name, "taken", taken_at),
                "name": name,
                "action": "taken",
                "occurred_at": taken_at,
                "recorded_at": taken_at or updated_at,
                "dose": None,
                "note": note,
            })
        elif taken_val is False and _is_placeholder(item):
            # C: placeholder → skip (remove from array)
            continue
        elif taken_val is False:
            # D: meaningful skip → action=skipped
            note = item.get("note")
            note = str(note).strip() if note else None
            if not note:
                continue  # safety: shouldn't reach here but be defensive

            new_meds.append({
                "medication_id": _migrate_medication_id(
                    day_id, idx, name, "skipped", None),
                "name": name,
                "action": "skipped",
                "occurred_at": None,
                "recorded_at": updated_at,
                "dose": None,
                "note": note,
            })

    updated["medications"] = new_meds
    updated["updated_at"] = timestamp

    return MigrationResult(updated, True)


def _infer_schema_version(day: Mapping[str, Any]) -> int:
    """Infer schema version for legacy docs that lack the field."""
    if "medications" in day:
        first_med = day["medications"][0] if day["medications"] else None
        if first_med and "medication_id" in first_med:
            return 2
        if first_med and "taken" in first_med:
            return 1
    return 1


def migrate_calendar_index(
    calendar: Mapping[str, Any],
    *,
    timestamp: str,
) -> MigrationResult:
    events = calendar.get("events", {})
    migrated_events: dict[str, Any] = {}
    changed = False
    for key, event in events.items():
        new_key = calendar_key(
            event.get("calendar_id", ""),
            event.get("event_id", key),
        )
        migrated_events[new_key] = event
        if new_key != key:
            changed = True

    if not changed:
        return MigrationResult(dict(calendar), False)

    updated = dict(calendar)
    updated["events"] = migrated_events
    updated["generated_at"] = timestamp
    return MigrationResult(updated, True)


def migrate_fridge_document(
    fridge: Mapping[str, Any],
    *,
    timestamp: str,
) -> MigrationResult:
    migrated_items: list[dict[str, Any]] = []
    changed = False
    for item in fridge.get("items", []):
        migrated_item = dict(item)
        category = migrated_item.get("category", "other")
        mapped = (
            category
            if category in CATEGORIES
            else CATEGORY_MAP.get(category, "other")
        )
        if mapped != category:
            migrated_item["category"] = mapped
            changed = True
        migrated_items.append(migrated_item)

    if not changed:
        return MigrationResult(dict(fridge), False)

    updated = dict(fridge)
    updated["items"] = migrated_items
    updated["updated_at"] = timestamp
    return MigrationResult(updated, True)


def calendar_key(calendar_id: str, event_id: str) -> str:
    return f"{calendar_id}::{event_id}"
