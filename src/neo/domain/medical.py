from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import uuid4

from ..errors import NotFoundError, ValidationError
from ..utils import now_iso, today_seoul


def empty_store() -> dict[str, Any]:
    return {"schema_version": 1, "records": [], "updated_at": now_iso()}


def cycle_status(last_date: str, cycle_days: int, today: date | None = None) -> dict[str, Any]:
    if cycle_days < 1:
        raise ValidationError("cycle_days must be >= 1")
    occurred = date.fromisoformat(last_date)
    current = today or today_seoul()
    next_due = occurred + timedelta(days=cycle_days)
    days_until = (next_due - current).days
    return {
        "days_since": (current - occurred).days,
        "next_due": next_due.isoformat(),
        "days_until_next": days_until,
        "overdue": max(0, -days_until),
    }


def add_record(
    store: dict[str, Any], *, provider: str, title: str, last_date: str,
    cycle_days: int | None = None, kind: str | None = None, note: str | None = None,
) -> tuple[dict[str, Any], str]:
    provider = provider.strip()
    title = title.strip()
    if not provider or not title:
        raise ValidationError("provider and title must not be empty")
    date.fromisoformat(last_date)
    if cycle_days is not None and cycle_days < 1:
        raise ValidationError("cycle_days must be >= 1")
    record_id = str(uuid4())
    record: dict[str, Any] = {
        "medical_id": record_id,
        "provider": provider,
        "title": title,
        "last_date": last_date,
        "cycle_days": cycle_days,
        "kind": kind.strip() if kind else None,
        "note": note.strip() if note else None,
        "updated_at": now_iso(),
    }
    result = {**store, "schema_version": 1, "records": [*store.get("records", []), record], "updated_at": now_iso()}
    return result, record_id


def record_event(store: dict[str, Any], medical_id: str, *, at: str, note: str | None = None) -> dict[str, Any]:
    date.fromisoformat(at)
    records = []
    found = False
    for item in store.get("records", []):
        if item.get("medical_id") == medical_id:
            found = True
            item = {**item, "last_date": at, "updated_at": now_iso()}
            if note is not None:
                item["note"] = note.strip() or None
        records.append(item)
    if not found:
        raise NotFoundError(f"Medical record not found: {medical_id}")
    return {**store, "records": records, "updated_at": now_iso()}


def remove_record(store: dict[str, Any], medical_id: str) -> dict[str, Any]:
    records = [item for item in store.get("records", []) if item.get("medical_id") != medical_id]
    if len(records) == len(store.get("records", [])):
        raise NotFoundError(f"Medical record not found: {medical_id}")
    return {**store, "records": records, "updated_at": now_iso()}


def with_status(store: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    records = []
    for item in store.get("records", []):
        rendered = dict(item)
        cycle_days = item.get("cycle_days")
        if cycle_days is not None:
            rendered["status"] = cycle_status(item["last_date"], cycle_days, today)
        records.append(rendered)
    return {**store, "records": records}
