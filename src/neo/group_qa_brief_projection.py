from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .brief_projection import (
    BriefProjection,
    brief_projection_to_dict,
    load_brief_projection,
)
from .group_qa_models import TrustedGroupBriefSummary
from .paths import NeoPaths


_SEOUL = ZoneInfo("Asia/Seoul")


def _clock(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(_SEOUL)
    if value.tzinfo is None:
        return value.replace(tzinfo=_SEOUL)
    return value.astimezone(_SEOUL)


def build_trusted_group_brief_summary(
    paths: NeoPaths,
    *,
    now: datetime | None = None,
) -> TrustedGroupBriefSummary | None:
    """Summarize the same in-memory projection used to render brief.md."""

    clock = _clock(now)
    try:
        projection = load_brief_projection(
            paths,
            generated_at=clock.isoformat(timespec="seconds"),
        )
    except Exception:
        return None
    return _summary_from_projection(projection)


def build_trusted_group_brief_context(
    paths: NeoPaths,
    *,
    now: datetime | None = None,
) -> tuple[str, TrustedGroupBriefSummary | None]:
    """Render trusted model context from structured data, never from Markdown.

    The JSON payload contains the same brief-visible fields that feed brief.md.
    It is serialized only for the model request and is not persisted as a new
    repository file.
    """

    clock = _clock(now)
    try:
        projection = load_brief_projection(
            paths,
            generated_at=clock.isoformat(timespec="seconds"),
        )
    except Exception:
        return "[trusted group brief projection unavailable]", None

    summary = _summary_from_projection(projection)
    payload = json.dumps(
        brief_projection_to_dict(projection),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    lines = [
        "[trusted group brief projection - canonical JSON, read-only]",
        "source=shared BriefProjection used by brief.md",
        "rendered_brief_file_read=false",
        f"pending_open_items={summary.open_pending_count}",
        f"medication_open_items={summary.open_medication_count}",
        f"project_open_tasks={summary.open_project_count}",
        f"brief_projection_json={payload}",
    ]
    return "\n".join(lines), summary


def _summary_from_projection(
    projection: BriefProjection,
) -> TrustedGroupBriefSummary:
    current_day = projection.current_day
    open_pending = sum(1 for item in projection.pending_items if not item.done)
    open_medications = (
        _count_missing_expected_medications(current_day)
        if current_day is not None
        else 0
    )
    open_project_tasks = sum(
        len(project.current_milestone.open_tasks)
        for project in projection.projects
        if project.current_milestone is not None
    )

    sections: list[tuple[str, tuple[str, ...]]] = []
    if projection.medical is not None:
        sections.append(("medical", (_compact(projection.medical),)))
    sections.append(
        (
            "pending",
            tuple(_compact(item) for item in projection.pending_items),
        )
    )
    if current_day is not None:
        sections.extend(
            [
                ("life_day", (_compact({
                    "date": current_day.date,
                    "wake_at": current_day.wake_at,
                    "sleep_at": current_day.sleep_at,
                    "status": current_day.status,
                    "workday_capacity": current_day.workday_capacity,
                }),)),
                ("mood", ((_compact(current_day.mood),) if current_day.mood is not None else ())),
                ("meals", tuple(_compact(item) for item in current_day.meals)),
                ("medications", tuple(_compact(item) for item in current_day.medications)),
                ("outings", tuple(_compact(item) for item in current_day.outings)),
                ("today_todos", tuple(_compact(item) for item in current_day.todos)),
                ("work_plan", tuple(_compact(item) for item in current_day.work_plan)),
                ("external_schedule", tuple(_compact(item) for item in current_day.external_schedule)),
            ]
        )
    sections.append(("projects", tuple(_compact(item) for item in projection.projects)))
    sections.append(("calendar", (_compact(projection.calendar),)))

    return TrustedGroupBriefSummary(
        generated_at=projection.generated_at,
        current_life_day=current_day.date if current_day is not None else None,
        sections=tuple(sections),
        open_pending_count=open_pending,
        open_medication_count=open_medications,
        open_project_count=open_project_tasks,
    )



def _count_missing_expected_medications(current_day: Any) -> int:
    from .domain.lifestyle import EXPECTED_MEDICATION_NAMES
    meds = getattr(current_day, "medications", ())
    taken_names = set()
    skipped_names = set()
    for m in meds:
        if getattr(m, "action", None) == "taken":
            taken_names.add(getattr(m, "name", ""))
        elif getattr(m, "action", None) == "skipped":
            skipped_names.add(getattr(m, "name", ""))
    return sum(
        1 for name in EXPECTED_MEDICATION_NAMES
        if name not in taken_names and name not in skipped_names
    )

def _compact(value: Any) -> str:
    if hasattr(value, "__dataclass_fields__"):
        value = asdict(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
