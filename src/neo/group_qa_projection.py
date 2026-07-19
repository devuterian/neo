from __future__ import annotations

import json
from datetime import date, datetime
from typing import Literal, Mapping
from zoneinfo import ZoneInfo

from .group_qa_models import GroupPublicStatus, TrustedGroupBriefSummary
from .group_qa_policy import bucket_time, redact_public_text
from .paths import NeoPaths
from .repository import Repository
from .transaction import read_json


_SEOUL = ZoneInfo("Asia/Seoul")


def _clock(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(_SEOUL)
    if value.tzinfo is None:
        return value.replace(tzinfo=_SEOUL)
    return value.astimezone(_SEOUL)


def _empty_status() -> GroupPublicStatus:
    return GroupPublicStatus(
        None,
        False,
        None,
        False,
        None,
        False,
        (),
        False,
        (),
        False,
        False,
        (),
        None,
        0,
        (),
        0,
        (),
        "unknown",
        "unknown",
    )


def _format_time(value: str | None) -> str | None:
    try:
        return datetime.fromisoformat(str(value)).strftime("%H:%M")
    except (TypeError, ValueError):
        return None


def _trusted_medical_projection(paths: NeoPaths, *, today: date) -> dict[str, object]:
    """Return the nearest recurring medical record without exposing notes."""

    try:
        raw = json.loads(paths.medical_file.read_text(encoding="utf-8"))
        from .domain.medical import with_status

        records = [item for item in with_status(raw, today)["records"] if "status" in item]
        if not records:
            return {}
        item = min(records, key=lambda value: value["status"]["days_until_next"])
        return {"last_date": item["last_date"], **item["status"]}
    except Exception:
        return {}


def _is_public_project(item: Mapping[str, object], allowlist: set[str]) -> bool:
    if not allowlist:
        return False
    candidates = (
        item.get("project_id"),
        item.get("project_title_snapshot"),
        item.get("task_id"),
        item.get("task_title_snapshot"),
    )
    return any(str(value).strip() in allowlist for value in candidates if value is not None)


def _wake_sleep_history(paths: NeoPaths, *, now: datetime) -> tuple[tuple | None, tuple | None, tuple | None]:
    records: list[tuple[str, datetime, str, str]] = []
    try:
        day_files = Repository(paths).day_files()
    except Exception:
        return None, None, None
    for day_path in day_files:
        try:
            day = read_json(day_path)
        except Exception:
            continue
        source_day = str(day.get("date") or day_path.stem)
        for field in ("wake_at", "sleep_at"):
            raw = day.get(field)
            if not isinstance(raw, str) or not raw.strip():
                continue
            try:
                point = datetime.fromisoformat(raw)
                point = point.replace(tzinfo=_SEOUL) if point.tzinfo is None else point.astimezone(_SEOUL)
            except ValueError:
                continue
            records.append((field, point, raw, source_day))
    wakes = sorted((item for item in records if item[0] == "wake_at"), key=lambda item: item[1])
    sleeps = sorted((item for item in records if item[0] == "sleep_at"), key=lambda item: item[1])
    today_wakes = [item for item in wakes if item[1].date() == now.date()]
    return (
        today_wakes[-1] if today_wakes else None,
        wakes[-1] if wakes else None,
        sleeps[-1] if sleeps else None,
    )


def build_group_public_status(
    paths: NeoPaths,
    *,
    now: datetime | None = None,
    public_project_allowlist: set[str] | None = None,
    detail_level: Literal["safe", "trusted"] = "safe",
) -> GroupPublicStatus:
    """Build the only day/medical DTO that group routes may consume."""

    try:
        _, day = Repository(paths).current_day_location()
    except Exception:
        return _empty_status()

    allowlist = public_project_allowlist or set()
    trusted = detail_level == "trusted"
    meals = tuple(
        item
        for item in (
            redact_public_text(meal.get("what", ""), allow_project_terms=True)
            for meal in day.get("meals", [])
        )
        if item
    )
    outings = list(day.get("outings", []))
    ongoing = any(not outing.get("returned_at") for outing in outings)
    places = (
        ()
        if ongoing
        else tuple(
            item
            for item in (
                redact_public_text(outing.get("place", ""), allow_project_terms=True)
                for outing in outings
            )
            if item
        )
    )
    todos = list(day.get("todolist", []))
    done = [todo for todo in todos if todo.get("done")]
    open_todos = [todo for todo in todos if not todo.get("done")]
    completed = tuple(
        item
        for item in (
            redact_public_text(todo.get("title", ""), allow_project_terms=True) for todo in done
        )
        if item
    )
    todo_items = tuple(
        item
        for item in (
            redact_public_text(todo.get("title", ""), allow_project_terms=True)
            for todo in open_todos
        )
        if item
    )
    sessions = list(day.get("work_sessions", []))
    open_sessions = [session for session in sessions if session.get("checked_out_at") is None]
    buckets = tuple(
        item for item in (bucket_time(session.get("checked_in_at")) for session in sessions) if item
    )
    meal_details = (
        tuple(
            (time, item)
            for meal in day.get("meals", [])
            if (time := _format_time(meal.get("occurred_at")))
            and (item := redact_public_text(meal.get("what", ""), allow_project_terms=True))
        )
        if trusted
        else ()
    )
    work_details = (
        tuple(
            "~".join(
                part
                for part in (
                    _format_time(session.get("checked_in_at")),
                    _format_time(session.get("checked_out_at")),
                )
                if part
            )
            for session in sessions
            if _format_time(session.get("checked_in_at"))
        )
        if trusted
        else ()
    )
    public_work = None
    for session in open_sessions:
        if _is_public_project(session, allowlist):
            public_work = redact_public_text(
                str(session.get("project_title_snapshot", "")), allow_project_terms=True
            )
            break

    is_working = bool(open_sessions)
    light: Literal["working", "resting", "out", "unknown"] = (
        "working" if is_working else "out" if ongoing else "resting"
    )
    availability: Literal["busy", "maybe_available", "unknown"] = (
        "busy" if is_working or ongoing else "maybe_available"
    )
    clock = _clock(now)
    today_wake, latest_wake, latest_sleep = _wake_sleep_history(paths, now=clock)
    naps = day.get("naps", [])
    ongoing_nap = any(
        isinstance(nap.get("started_at"), str)
        and datetime.fromisoformat(nap["started_at"]).astimezone(_SEOUL) <= clock
        and nap.get("ended_at") is None
        for nap in naps
        if isinstance(nap, dict)
    )
    medical = _trusted_medical_projection(paths, today=clock.date()) if trusted else {}

    return GroupPublicStatus(
        date=day.get("date"),
        wake_recorded=bool(day.get("wake_at")),
        wake_time_bucket=bucket_time(day.get("wake_at")),
        sleep_recorded=bool(day.get("sleep_at")),
        sleep_time_bucket=bucket_time(day.get("sleep_at")),
        meal_recorded=bool(day.get("meals")),
        meal_public_items=meals,
        outing_recorded=bool(outings),
        outing_public_places=places,
        has_ongoing_outing=ongoing,
        is_working_now=is_working,
        work_time_buckets=buckets,
        public_work_summary=public_work,
        completed_count=len(done),
        public_completed_items=completed,
        todo_count=len(open_todos),
        public_todo_items=todo_items,
        availability=availability,
        light_status=light,
        medical_available=bool(medical),
        medical_last_date=medical.get("last_date"),
        medical_days_since=medical.get("days_since"),
        medical_next_due=medical.get("next_due"),
        medical_days_until_next=medical.get("days_until_next"),
        medical_overdue=medical.get("overdue"),
        trusted=trusted,
        wake_time=_format_time(today_wake[2]) if trusted and today_wake else None,
        sleep_time=_format_time(day.get("sleep_at")) if trusted else None,
        meal_details=meal_details,
        work_session_details=work_details,
        today_wake_at=today_wake[1].isoformat(timespec="minutes") if trusted and today_wake else None,
        today_wake_date=today_wake[1].date().isoformat() if trusted and today_wake else None,
        today_wake_is_same_local_date=bool(today_wake),
        latest_wake_at=latest_wake[1].isoformat(timespec="minutes") if trusted and latest_wake else None,
        latest_wake_date=latest_wake[1].date().isoformat() if trusted and latest_wake else None,
        latest_wake_source_day=latest_wake[3] if trusted and latest_wake else None,
        latest_sleep_at=latest_sleep[1].isoformat(timespec="minutes") if trusted and latest_sleep else None,
        latest_sleep_date=latest_sleep[1].date().isoformat() if trusted and latest_sleep else None,
        latest_sleep_source_day=latest_sleep[3] if trusted and latest_sleep else None,
        has_ongoing_nap=ongoing_nap if trusted else False,
    )


def _open_pending_count(paths: NeoPaths) -> int:
    try:
        data = read_json(paths.pending_file)
        return sum(1 for item in data.get("items", []) if not item.get("done"))
    except Exception:
        return 0


def _open_project_task_count(paths: NeoPaths) -> int:
    count = 0
    try:
        projects = Repository(paths).load_projects()
    except Exception:
        return 0
    for location in projects:
        project = location.data
        if project.get("status") in {"complete", "cancelled"}:
            continue
        for milestone in project.get("milestones", []):
            for task in milestone.get("tasks", []):
                if task.get("status") not in {"done", "cancelled"}:
                    count += 1
    return count


def build_trusted_group_brief_summary(
    paths: NeoPaths,
    *,
    now: datetime | None = None,
) -> TrustedGroupBriefSummary | None:
    """Build a sanitized summary from canonical JSON, never from rendered brief.md."""

    clock = _clock(now)
    try:
        _, day = Repository(paths).current_day_location()
    except Exception:
        return None
    pending_count = _open_pending_count(paths)
    from .domain.lifestyle import EXPECTED_MEDICATION_NAMES
    medications = list(day.get("medications", []))
    taken_names = set()
    skipped_names = set()
    for m in medications:
        if m.get("action") == "taken":
            taken_names.add(m.get("name", ""))
        elif m.get("action") == "skipped":
            skipped_names.add(m.get("name", ""))
    medication_open = sum(
        1 for name in EXPECTED_MEDICATION_NAMES
        if name not in taken_names and name not in skipped_names
    )
    project_open = _open_project_task_count(paths)
    external_count = len(day.get("external_schedule_snapshot", []))
    sections = (
        (
            "life_day",
            (
                f"date={day.get('date') or 'unknown'}",
                f"wake_recorded={'true' if day.get('wake_at') else 'false'}",
                f"sleep_recorded={'true' if day.get('sleep_at') else 'false'}",
            ),
        ),
        ("pending", (f"open_items={pending_count}",)),
        ("medication", (f"open_items={medication_open}", f"records={len(medications)}")),
        ("today_plan", (f"open_todos={sum(1 for item in day.get('todolist', []) if not item.get('done'))}",)),
        ("projects", (f"open_tasks={project_open}",)),
        ("calendar", (f"snapshot_events={external_count}",)),
    )
    return TrustedGroupBriefSummary(
        generated_at=clock.isoformat(timespec="seconds"),
        current_life_day=str(day.get("date")) if day.get("date") else None,
        sections=sections,
        open_pending_count=pending_count,
        open_medication_count=medication_open,
        open_project_count=project_open,
    )


def build_trusted_group_brief_context(
    paths: NeoPaths,
    *,
    now: datetime | None = None,
) -> tuple[str, TrustedGroupBriefSummary | None]:
    summary = build_trusted_group_brief_summary(paths, now=now)
    if summary is None:
        return "[trusted group structured context unavailable]", None
    lines = ["[trusted group structured context - canonical JSON, sanitized, read-only]"]
    lines.append(f"generated_at={summary.generated_at or 'missing'}")
    lines.append(f"current_life_day={summary.current_life_day or 'missing'}")
    lines.append(f"pending_open_items={summary.open_pending_count}")
    lines.append(f"medication_open_items={summary.open_medication_count}")
    lines.append(f"project_open_tasks={summary.open_project_count}")
    for key, values in summary.sections:
        lines.append(f"[{key}]")
        lines.extend(values)
    return "\n".join(lines), summary


def build_trusted_group_model_context(
    status: GroupPublicStatus,
    *,
    now_local: datetime | None = None,
    timezone_name: str | None = None,
) -> str:
    """Render only fields already present in the structured public DTO."""

    lines = ["[trusted group read-only context]"]
    if now_local is not None:
        clock = _clock(now_local)
        lines.extend(
            [
                f"now_local_iso={clock.isoformat(timespec='minutes')}",
                f"now_local_hhmm={clock.strftime('%H:%M')}",
                f"today_local_date={clock.date().isoformat()}",
                f"timezone={timezone_name or 'Asia/Seoul'}",
                "current_time_source=gateway_clock",
            ]
        )
    lines.extend(
        [
            f"active_day={status.date or 'unknown'}",
            f"today_wake_at={status.today_wake_at or 'missing'}",
            f"today_wake_date={status.today_wake_date or 'missing'}",
            f"today_wake_is_same_local_date={'true' if status.today_wake_is_same_local_date else 'false'}",
            f"latest_wake_at={status.latest_wake_at or 'missing'}",
            f"latest_wake_date={status.latest_wake_date or 'missing'}",
            f"latest_wake_source_day={status.latest_wake_source_day or 'missing'}",
            f"latest_sleep_at={status.latest_sleep_at or 'missing'}",
            f"latest_sleep_date={status.latest_sleep_date or 'missing'}",
            f"latest_sleep_source_day={status.latest_sleep_source_day or 'missing'}",
            f"wake={status.today_wake_at or 'unknown'}",
            f"sleep_current_life_day={status.sleep_time or ('recorded' if status.sleep_recorded else 'not_recorded')}",
            f"sleep={status.sleep_time or ('recorded_in_history' if status.latest_sleep_at else ('recorded' if status.sleep_recorded else 'not_recorded'))}",
        ]
    )
    if status.trusted and status.has_ongoing_nap:
        lines.append("current_sleep_state=낮잠잔다")
    awake_minutes: int | None = None
    basis = "missing"
    if now_local is not None and status.latest_wake_at:
        clock = _clock(now_local)
        try:
            latest_wake = datetime.fromisoformat(status.latest_wake_at)
            latest_sleep = datetime.fromisoformat(status.latest_sleep_at) if status.latest_sleep_at else None
            if latest_wake.tzinfo is None:
                latest_wake = latest_wake.replace(tzinfo=_SEOUL)
            if latest_sleep is not None and latest_sleep.tzinfo is None:
                latest_sleep = latest_sleep.replace(tzinfo=_SEOUL)
            if latest_wake <= clock and not (latest_sleep and latest_sleep >= latest_wake):
                awake_minutes = max(0, int((clock - latest_wake).total_seconds() // 60))
                basis = "today_wake" if status.today_wake_at else "latest_wake"
        except (TypeError, ValueError):
            pass
    lines.append(f"awake_duration_basis={basis}")
    lines.append(
        f"today_awake_duration_available={'true' if status.today_wake_at and awake_minutes is not None else 'false'}"
    )
    lines.append(
        "today_wake_missing_reason=none"
        if status.today_wake_at
        else "today_wake_missing_reason=no_wake_record_for_today"
    )
    if awake_minutes is not None:
        hours, minutes = divmod(awake_minutes, 60)
        lines.append(f"awake_duration_from_latest_wake_minutes={awake_minutes}")
        lines.append(f"awake_duration_from_latest_wake_human={hours}시간 {minutes}분")
    else:
        lines.append("awake_duration_from_latest_wake=not_calculated")
    if status.meal_details:
        lines.append("meals=" + "; ".join(f"{time} {item}" for time, item in status.meal_details))
        lines.append("last_meal=" + " ".join(status.meal_details[-1]))
    else:
        lines.append("meals=none_recorded")
    lines.append(
        f"outing={'ongoing' if status.has_ongoing_outing else ('recorded' if status.outing_recorded else 'none_recorded')}"
    )
    lines.append(f"working_now={'yes' if status.is_working_now else 'no'}")
    lines.append(f"completed_today={status.completed_count}")
    lines.append(f"remaining_todos={status.todo_count}")
    if status.medical_available:
        values = {
            "last_date": status.medical_last_date,
            "days_since": status.medical_days_since,
            "next_due": status.medical_next_due,
            "days_until_next": status.medical_days_until_next,
            "overdue": status.medical_overdue,
        }
        lines.append("medical=" + ", ".join(f"{key}={value}" for key, value in values.items() if value is not None))
    return "\n".join(lines)
