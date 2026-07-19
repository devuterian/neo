"""Append-only audit log for mutation operations.

Records corrections (correct action) so they persist in workspace history
beyond the JSON response. Uses the same JSONL pattern as message-log.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import NeoPaths

Json = dict[str, Any]


def _audit_dir(paths: NeoPaths) -> Path:
    return paths.root / "data" / "audit"


def _today_audit_path(paths: NeoPaths) -> Path:
    now = datetime.now(timezone.utc)
    return _audit_dir(paths) / (now.strftime("%Y-%m-%d") + ".jsonl")


def record_correction(
    paths: NeoPaths,
    *,
    resource: str,
    target: str,
    changed_fields: list[str],
    before: Json | None,
    after: Json | None,
    reason: str,
) -> Json:
    """Append a correction audit record. Returns the record."""
    audit_dir = _audit_dir(paths)
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_path = _today_audit_path(paths)

    record: Json = {
        "operation_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": "correct",
        "resource": resource,
        "target": target,
        "changed_fields": changed_fields,
        "before": before,
        "after": after,
        "reason": reason,
    }

    with audit_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return record


__all__ = ["record_correction"]
