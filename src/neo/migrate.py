from __future__ import annotations

from pathlib import Path
from typing import Any

from .domain import private_spark as spark_domain
from .migration_steps import (
    CATEGORY_MAP,
    calendar_key,
    migrate_calendar_index,
    migrate_day_document,
    migrate_fridge_document,
)
from .paths import NeoPaths
from .transaction import read_json
from .utils import now_iso
from .workspace import commit_workspace


def migrate_state(paths: NeoPaths) -> dict[str, Any]:
    day_updates: dict[Path, dict[str, Any]] = {}
    for day_file in sorted(paths.days.glob("*/*.json")):
        result = migrate_day_document(
            read_json(day_file),
            timestamp=now_iso(),
        )
        if result.changed:
            day_updates[day_file] = result.document

    calendar_update = None
    if paths.calendar_index.is_file():
        result = migrate_calendar_index(
            read_json(paths.calendar_index),
            timestamp=now_iso(),
        )
        if result.changed:
            calendar_update = result.document

    fridge_update = None
    if paths.fridge_file.is_file():
        result = migrate_fridge_document(
            read_json(paths.fridge_file),
            timestamp=now_iso(),
        )
        if result.changed:
            fridge_update = result.document

    if day_updates or calendar_update is not None or fridge_update is not None:
        commit_workspace(
            paths,
            day_updates=day_updates,
            calendar_update=calendar_update,
            fridge_update=fridge_update,
        )

    spark = spark_domain.migrate_legacy_records(paths)
    return {
        "ok": True,
        "days": len(day_updates),
        "calendar": calendar_update is not None,
        "fridge": fridge_update is not None,
        "private_spark": spark,
    }
