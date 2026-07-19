from __future__ import annotations

from typing import Any

from ..utils import now_iso
from ..migrate import calendar_key


def normalize_calendar_index(payload: dict[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result["schema_version"] = 1
    result["generated_at"] = now_iso()
    result["events"] = {calendar_key(e["calendar_id"], e["event_id"]): e for e in result.get("events", {}).values()}
    return result
