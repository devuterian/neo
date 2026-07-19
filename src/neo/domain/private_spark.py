from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..errors import NotFoundError, ValidationError
from ..paths import NeoPaths
from ..transaction import read_json, repository_lock, write_batch
from ..utils import now_iso, now_seoul, parse_datetime
from ..validation import validate_document
from ..workspace import _git_commit

KINDS = {"solo", "together", "none"}
PRIVATE_FIELDS = {"partner", "mood", "condition", "discomfort", "note"}
RECORD_FIELDS = {
    "id",
    "life_day",
    "kind",
    "partner",
    "started_at",
    "ended_at",
    "mood",
    "condition",
    "discomfort",
    "note",
    "created_at",
    "updated_at",
}


def month_path(paths: NeoPaths, month: str) -> Path:
    _validate_month(month)
    return paths.private_spark / month[:4] / f"{month}.json"


def primary_datetime(record: dict[str, Any]) -> datetime:
    value = record.get("ended_at") or record.get("started_at") or record.get("created_at")
    return parse_datetime(value)


def primary_month(record: dict[str, Any]) -> str:
    return primary_datetime(record).strftime("%Y-%m")


def create_store() -> dict[str, Any]:
    return {"schema_version": 1, "records": []}


def load_store(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return create_store()
    return read_json(path)


def spark_files(paths: NeoPaths) -> list[Path]:
    return sorted(paths.private_spark.glob("*/*.json"))


def load_all_records(paths: NeoPaths) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in spark_files(paths):
        store = read_json(path)
        for record in store.get("records", []):
            records.append(dict(record))
    return sorted(records, key=lambda item: primary_datetime(item))


def make_record(
    *,
    kind: str,
    life_day: str,
    partner: str | None = None,
    started_at: str | None = None,
    ended_at: str | None = None,
    mood: str | None = None,
    condition: str | None = None,
    discomfort: str | None = None,
    note: str | None = None,
    allow_imprecise: bool = False,
) -> dict[str, Any]:
    if kind not in KINDS:
        raise ValidationError(f"Invalid kind: {kind}")
    if kind in {"solo", "together"} and ended_at is None and not allow_imprecise:
        raise ValidationError("--ended-at is required for solo/together unless --allow-imprecise is set")
    if kind == "none":
        partner = None

    started = _normalize_optional_datetime(started_at)
    ended = _normalize_optional_datetime(ended_at)
    if started and ended and parse_datetime(ended) < parse_datetime(started):
        raise ValidationError("ended_at cannot be earlier than started_at")

    created = now_iso()
    id_source = parse_datetime(ended or started or created)
    record = {
        "id": f"spark_{id_source.strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:4]}",
        "life_day": life_day,
        "kind": kind,
        "partner": _blank_to_none(partner),
        "started_at": started,
        "ended_at": ended,
        "mood": _blank_to_none(mood),
        "condition": _blank_to_none(condition),
        "discomfort": _blank_to_none(discomfort),
        "note": _blank_to_none(note),
        "created_at": created,
        "updated_at": created,
    }
    return record


def log_record(paths: NeoPaths, record: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    path = month_path(paths, primary_month(record))
    store = load_store(path)
    _ensure_unique_id(paths, record["id"])
    updated = {**store, "records": [*store.get("records", []), record]}
    _write_spark(paths, {path: updated})
    return path, record


def list_records(
    paths: NeoPaths,
    *,
    month: str | None = None,
    life_day: str | None = None,
    last_days: int | None = None,
    include_notes: bool = False,
) -> list[dict[str, Any]]:
    records = load_all_records(paths)
    if month:
        _validate_month(month)
        records = [record for record in records if primary_month(record) == month]
    if life_day:
        records = [record for record in records if record.get("life_day") == life_day]
    if last_days is not None:
        cutoff = now_seoul() - timedelta(days=last_days)
        records = [record for record in records if primary_datetime(record) >= cutoff]
    return [_public_record(record, include_notes=include_notes) for record in records]


def edit_record(paths: NeoPaths, record_id: str, changes: dict[str, Any]) -> dict[str, Any]:
    path, store, index = _find_record(paths, record_id)
    record = dict(store["records"][index])
    for key, value in changes.items():
        if value is not None:
            record[key] = _normalize_optional_datetime(value) if key in {"started_at", "ended_at"} else _blank_to_none(value)
    if record["kind"] not in KINDS:
        raise ValidationError(f"Invalid kind: {record['kind']}")
    if record.get("started_at") and record.get("ended_at") and parse_datetime(record["ended_at"]) < parse_datetime(record["started_at"]):
        raise ValidationError("ended_at cannot be earlier than started_at")
    record["updated_at"] = now_iso()
    store["records"][index] = record
    _write_spark(paths, {path: store})
    return _public_record(record, include_notes=True)


def remove_record(paths: NeoPaths, record_id: str) -> dict[str, Any]:
    path, store, index = _find_record(paths, record_id)
    removed = store["records"].pop(index)
    updates: dict[Path, dict[str, Any]] = {}
    deletes: set[Path] = set()
    if store["records"]:
        updates[path] = store
    else:
        deletes.add(path)
    _write_spark(paths, updates, deletes)
    return {
        "ok": True,
        "id": removed["id"],
        "warning": "Removed from the current JSON file only. Existing Git history may still contain prior content.",
    }


def build_report(
    paths: NeoPaths,
    *,
    month: str | None = None,
    life_day: str | None = None,
    last_days: int | None = None,
    include_notes: bool = False,
) -> str:
    records = list_records(paths, month=month, life_day=life_day, last_days=last_days, include_notes=True)
    title_range = month or life_day or (f"last {last_days}d" if last_days else "all")
    lines = [f"# private spark report ({title_range})", ""]
    lines.append(f"- total: {len(records)}")
    by_kind = Counter(record["kind"] for record in records)
    for kind in sorted(KINDS):
        lines.append(f"- {kind}: {by_kind.get(kind, 0)}")

    by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_hour: Counter[int] = Counter()
    for record in records:
        by_day[record["life_day"]].append(record)
        when = record.get("ended_at") or record.get("started_at")
        if when:
            by_hour[parse_datetime(when).hour] += 1

    lines.extend(["", "## life-day"])
    for day, day_records in sorted(by_day.items()):
        lines.append(f"- {day}: {len(day_records)}")
        for record in day_records:
            when = record.get("ended_at") or record.get("started_at") or "time unknown"
            lines.append(f"  - {record['id']} / {record['kind']} / {when}")

    lines.extend(["", "## time pattern"])
    if by_hour:
        for hour, count in sorted(by_hour.items()):
            lines.append(f"- {hour:02d}:00: {count}")
    else:
        lines.append("- no time data")

    for field in ("mood", "condition", "discomfort"):
        values = Counter(record[field] for record in records if record.get(field))
        lines.extend(["", f"## {field}"])
        if values:
            for value, count in values.most_common():
                lines.append(f"- {value}: {count}")
        else:
            lines.append("- none")

    if include_notes:
        lines.extend(["", "## notes"])
        notes = [record for record in records if record.get("note")]
        if notes:
            for record in notes:
                lines.append(f"- {record['life_day']} / {record['id']}: {record['note']}")
        else:
            lines.append("- none")

    return "\n".join(lines) + "\n"


def write_report(markdown: str, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")
    return output


def doctor_summary(paths: NeoPaths) -> dict[str, Any]:
    records = load_all_records(paths)
    month = now_seoul().strftime("%Y-%m")
    this_month = [record for record in records if primary_month(record) == month]
    latest = records[-1] if records else None
    return {
        "status": "available",
        "records_this_month": len(this_month),
        "latest_record_life_day": latest.get("life_day") if latest else None,
        "schema_valid": True,
    }


def migrate_legacy_records(paths: NeoPaths) -> dict[str, int]:
    updates: dict[Path, dict[str, Any]] = {}
    changed_records = 0
    for path in spark_files(paths):
        original = read_json(path)
        migrated, count = migrate_store(original, path)
        if migrated != original:
            updates[path] = migrated
            changed_records += count
    if updates:
        _write_spark(paths, updates)
    return {"files": len(updates), "records": changed_records}


def migrate_store(value: Any, path: Path | None = None) -> tuple[dict[str, Any], int]:
    if isinstance(value, list):
        records = value
        store: dict[str, Any] = create_store()
    elif isinstance(value, dict):
        records = value.get("records", [])
        store = {"schema_version": value.get("schema_version", 1), "records": []}
    else:
        raise ValidationError("private spark legacy store must be an object or record array")
    if not isinstance(records, list):
        raise ValidationError("private spark records must be an array")

    migrated_records: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    changed = 0
    for index, record in enumerate(records):
        migrated = migrate_record(record, index=index, used_ids=used_ids)
        if migrated != record:
            changed += 1
        migrated_records.append(migrated)
    store["records"] = migrated_records
    if isinstance(value, dict) and store.get("schema_version") != value.get("schema_version"):
        changed += 1
    if path is not None and isinstance(value, dict) and "records" not in value:
        changed += 1
    return store, changed


def migrate_record(record: Any, *, index: int = 0, used_ids: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValidationError("private spark legacy record must be an object")
    used_ids = used_ids if used_ids is not None else set()
    ended = _first_datetime(record, "ended_at", "ended", "at", "occurred_at", "time")
    started = _first_datetime(record, "started_at", "started", "started_on")
    created = _first_datetime(record, "created_at") or ended or started or now_iso()
    updated = _first_datetime(record, "updated_at") or created
    primary = ended or started or created

    kind = _legacy_kind(record)
    partner = _blank_to_none(record.get("partner"))
    if kind is None:
        kind = "together" if partner else "solo"
    if kind == "none":
        partner = None

    life_day = _blank_to_none(record.get("life_day")) or parse_datetime(primary).date().isoformat()
    migrated = {
        "id": _blank_to_none(record.get("id")) or _legacy_id(record, primary, index),
        "life_day": life_day,
        "kind": kind,
        "partner": partner,
        "started_at": started,
        "ended_at": ended,
        "mood": _blank_to_none(record.get("mood")),
        "condition": _blank_to_none(record.get("condition")),
        "discomfort": _blank_to_none(record.get("discomfort")),
        "note": _blank_to_none(record.get("note") or record.get("text")),
        "created_at": created,
        "updated_at": updated,
    }
    while migrated["id"] in used_ids:
        migrated["id"] = _legacy_id({**record, "_duplicate": migrated["id"]}, primary, index + len(used_ids))
    used_ids.add(migrated["id"])
    if migrated["started_at"] and migrated["ended_at"] and parse_datetime(migrated["ended_at"]) < parse_datetime(migrated["started_at"]):
        raise ValidationError("ended_at cannot be earlier than started_at")
    return migrated


def _write_spark(
    paths: NeoPaths,
    updates: dict[Path, dict[str, Any]],
    deletes: set[Path] | None = None,
) -> None:
    deletes = deletes or set()
    with repository_lock(paths):
        for path, store in updates.items():
            validate_document(paths, store, "private-spark.schema.json", path.relative_to(paths.root).as_posix())
        write_batch(paths, updates, delete_paths=deletes)
        _git_commit(paths, list(updates), deletes)


def _find_record(paths: NeoPaths, record_id: str) -> tuple[Path, dict[str, Any], int]:
    for path in spark_files(paths):
        store = read_json(path)
        for index, record in enumerate(store.get("records", [])):
            if record.get("id") == record_id:
                return path, store, index
    raise NotFoundError(f"private spark record not found: {record_id}")


def _ensure_unique_id(paths: NeoPaths, record_id: str) -> None:
    try:
        _find_record(paths, record_id)
    except NotFoundError:
        return
    raise ValidationError(f"Duplicate private spark id: {record_id}")


def _normalize_optional_datetime(value: str | None) -> str | None:
    if value is None:
        return None
    return parse_datetime(value).isoformat(timespec="seconds")


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


def _public_record(record: dict[str, Any], *, include_notes: bool = False) -> dict[str, Any]:
    public = {
        "id": record["id"],
        "kind": record["kind"],
        "life_day": record["life_day"],
        "started_at": record.get("started_at"),
        "ended_at": record.get("ended_at"),
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
    }
    if include_notes:
        for key in PRIVATE_FIELDS:
            public[key] = record.get(key)
    return public


def _validate_month(month: str) -> None:
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError as exc:
        raise ValidationError(f"Invalid month: {month}. Expected YYYY-MM") from exc


def _first_datetime(record: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = record.get(key)
        if value:
            return _normalize_optional_datetime(str(value))
    return None


def _legacy_kind(record: dict[str, Any]) -> str | None:
    raw = _blank_to_none(record.get("kind") or record.get("type") or record.get("category"))
    if raw is None:
        return None
    normalized = raw.casefold()
    if normalized in {"solo", "self", "masturbation", "자위", "혼자"}:
        return "solo"
    if normalized in {"together", "sex", "partner", "with_partner", "섹스", "관계", "같이"}:
        return "together"
    if normalized in {"none", "no", "없음", "없었음", "없었어"}:
        return "none"
    raise ValidationError(f"Invalid legacy private spark kind: {raw}")


def _legacy_id(record: dict[str, Any], primary: str, index: int) -> str:
    digest = hashlib.sha1(
        json.dumps(record, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    dt = parse_datetime(primary)
    return f"spark_{dt.strftime('%Y%m%d_%H%M%S')}_{digest[index:index + 4] or digest[:4]}"
