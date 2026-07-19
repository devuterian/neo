from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..errors import ConflictError, ValidationError
from ..utils import new_uuid, new_uuid5, now_iso, parse_datetime

MEAL_TAGS = {"breakfast", "lunch", "dinner", "snack"}


def add_meal(day: dict[str, Any], *, tag: str, what: str, at: str | None = None) -> dict[str, Any]:
    if tag not in MEAL_TAGS:
        raise ValidationError(f"meal tag must be one of {sorted(MEAL_TAGS)}")
    what = what.strip()
    if not what:
        raise ValidationError("meal what must not be empty")
    result = deepcopy(day)
    result["meals"].append({
        "meal_id": new_uuid(),
        "occurred_at": parse_datetime(at).isoformat(timespec="seconds"),
        "tag": tag,
        "what": what,
    })
    result["updated_at"] = now_iso()
    return result


def remove_meal(day: dict[str, Any], meal_id: str) -> dict[str, Any]:
    result = deepcopy(day)
    target = next((m for m in result["meals"] if m["meal_id"] == meal_id), None)
    if target is None:
        raise ValidationError(f"Meal not found: {meal_id}")
    result["meals"].remove(target)
    result["updated_at"] = now_iso()
    return result


def set_mood(day: dict[str, Any], summary: str, reason: str | None = None) -> dict[str, Any]:
    result = deepcopy(day)
    entry: dict[str, Any] = {"summary": summary.strip()}
    if reason:
        entry["reason"] = reason.strip()
    result["mood"] = entry
    result["updated_at"] = now_iso()
    return result


def clear_mood(day: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(day)
    result["mood"] = None
    result["updated_at"] = now_iso()
    return result


def add_outing(day: dict[str, Any], *, left_at: str | None = None, place: str, purpose: str | None = None) -> dict[str, Any]:
    result = deepcopy(day)
    if any(o["returned_at"] is None for o in result["outings"]):
        raise ConflictError("Cannot add a new outing while another is ongoing")
    place = place.strip()
    if not place:
        raise ValidationError("outing place must not be empty")
    result["outings"].append({
        "outing_id": new_uuid(),
        "left_at": parse_datetime(left_at).isoformat(timespec="seconds"),
        "returned_at": None,
        "place": place,
        "purpose": purpose.strip() if purpose else None,
    })
    result["updated_at"] = now_iso()
    return result


def return_from_outing(day: dict[str, Any], outing_id: str, at: str | None = None) -> dict[str, Any]:
    result = deepcopy(day)
    target = next((o for o in result["outings"] if o["outing_id"] == outing_id), None)
    if target is None:
        raise ValidationError(f"Outing not found: {outing_id}")
    if target["returned_at"] is not None:
        raise ConflictError("Outing already marked as returned")
    returned = parse_datetime(at)
    left = parse_datetime(target["left_at"])
    if returned < left:
        raise ValidationError("Return time cannot precede leave time")
    target["returned_at"] = returned.isoformat(timespec="seconds")
    result["updated_at"] = now_iso()
    return result


def remove_outing(day: dict[str, Any], outing_id: str) -> dict[str, Any]:
    result = deepcopy(day)
    target = next((o for o in result["outings"] if o["outing_id"] == outing_id), None)
    if target is None:
        raise ValidationError(f"Outing not found: {outing_id}")
    result["outings"].remove(target)
    result["updated_at"] = now_iso()
    return result


# ============================================================
# Medication — event record model (schema v2)
# ============================================================

# Public Neo has no built-in medication regimen. Deployments may supply their
# own reminder policy without changing the medication event model.
EXPECTED_MEDICATION_NAMES: tuple[str, ...] = ()


def add_medication_event(
    day: dict[str, Any],
    *,
    name: str,
    action: str,
    occurred_at: str | None = None,
    dose: str | None = None,
    note: str | None = None,
) -> tuple[dict[str, Any], str]:
    name = name.strip()
    if not name:
        raise ValidationError("medication name must not be empty")
    if action not in ("taken", "skipped"):
        raise ValidationError("medication action must be taken or skipped")

    occurred = parse_datetime(occurred_at).isoformat(timespec="seconds") if occurred_at else now_iso()
    recorded = now_iso()
    medication_id = new_uuid()

    result = deepcopy(day)
    result["medications"].append({
        "medication_id": medication_id,
        "name": name,
        "action": action,
        "occurred_at": occurred,
        "recorded_at": recorded,
        "dose": dose,
        "note": note.strip() if note else None,
    })
    result["updated_at"] = recorded
    return result, medication_id


def remove_medication_event(
    day: dict[str, Any],
    medication_id: str,
) -> dict[str, Any]:
    result = deepcopy(day)
    target = next((m for m in result["medications"] if m["medication_id"] == medication_id), None)
    if target is None:
        raise ValidationError(f"Medication event not found: {medication_id}")
    result["medications"].remove(target)
    result["updated_at"] = now_iso()
    return result


def medication_status(day: dict[str, Any]) -> dict[str, Any]:
    meds: list[dict[str, Any]] = day.get("medications", [])
    taken_counts: dict[str, int] = {}
    skipped: list[str] = []
    for m in meds:
        if m["action"] == "taken":
            taken_counts[m["name"]] = taken_counts.get(m["name"], 0) + 1
        elif m["action"] == "skipped":
            skipped.append(m["name"])

    missing: list[str] = []
    expected = list(EXPECTED_MEDICATION_NAMES)
    for name in expected:
        if name not in taken_counts and name not in skipped:
            missing.append(name)

    return {
        "expected": expected,
        "missing": missing,
        "taken_counts": taken_counts,
        "skipped": skipped,
        "total_records": len(meds),
    }


SHOWER_TYPES = {"shower", "bath"}


def add_shower(
    day: dict[str, Any],
    *,
    started_at: str | None = None,
    shower_type: str | None = None,
) -> dict[str, Any]:
    if shower_type is not None and shower_type not in SHOWER_TYPES:
        raise ValidationError(f"shower type must be one of {sorted(SHOWER_TYPES)} or null")
    result = deepcopy(day)
    if any(s["ended_at"] is None for s in result.get("showers", [])):
        raise ConflictError("Cannot start a new shower while another is ongoing")
    result.setdefault("showers", []).append({
        "shower_id": new_uuid(),
        "started_at": parse_datetime(started_at).isoformat(timespec="seconds"),
        "ended_at": None,
        "type": shower_type,
    })
    result["updated_at"] = now_iso()
    return result


def finish_shower(day: dict[str, Any], shower_id: str, ended_at: str | None = None) -> dict[str, Any]:
    result = deepcopy(day)
    target = next((s for s in result.get("showers", []) if s["shower_id"] == shower_id), None)
    if target is None:
        raise ValidationError(f"Shower not found: {shower_id}")
    if target["ended_at"] is not None:
        raise ConflictError("Shower already finished")
    ended = parse_datetime(ended_at)
    started = parse_datetime(target["started_at"])
    if ended < started:
        raise ValidationError("End time cannot precede start time")
    target["ended_at"] = ended.isoformat(timespec="seconds")
    result["updated_at"] = now_iso()
    return result


def remove_shower(day: dict[str, Any], shower_id: str) -> dict[str, Any]:
    result = deepcopy(day)
    target = next((s for s in result.get("showers", []) if s["shower_id"] == shower_id), None)
    if target is None:
        raise ValidationError(f"Shower not found: {shower_id}")
    result["showers"].remove(target)
    result["updated_at"] = now_iso()
    return result


def add_hair_dry(
    day: dict[str, Any],
    *,
    started_at: str | None = None,
) -> dict[str, Any]:
    result = deepcopy(day)
    if any(h["ended_at"] is None for h in result.get("hair_dries", [])):
        raise ConflictError("Cannot start a new hair dry while another is ongoing")
    result.setdefault("hair_dries", []).append({
        "hair_dry_id": new_uuid(),
        "started_at": parse_datetime(started_at).isoformat(timespec="seconds"),
        "ended_at": None,
    })
    result["updated_at"] = now_iso()
    return result


def finish_hair_dry(day: dict[str, Any], hair_dry_id: str, ended_at: str | None = None) -> dict[str, Any]:
    result = deepcopy(day)
    target = next((h for h in result.get("hair_dries", []) if h["hair_dry_id"] == hair_dry_id), None)
    if target is None:
        raise ValidationError(f"Hair dry not found: {hair_dry_id}")
    if target["ended_at"] is not None:
        raise ConflictError("Hair dry already finished")
    ended = parse_datetime(ended_at)
    started = parse_datetime(target["started_at"])
    if ended < started:
        raise ValidationError("End time cannot precede start time")
    target["ended_at"] = ended.isoformat(timespec="seconds")
    result["updated_at"] = now_iso()
    return result


def remove_hair_dry(day: dict[str, Any], hair_dry_id: str) -> dict[str, Any]:
    result = deepcopy(day)
    target = next((h for h in result.get("hair_dries", []) if h["hair_dry_id"] == hair_dry_id), None)
    if target is None:
        raise ValidationError(f"Hair dry not found: {hair_dry_id}")
    result["hair_dries"].remove(target)
    result["updated_at"] = now_iso()
    return result
