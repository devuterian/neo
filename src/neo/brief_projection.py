from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .paths import NeoPaths
from .repository import Repository
from .transaction import read_json
from .utils import now_iso


@dataclass(frozen=True)
class BriefMedical:
    days_since: int | None
    last_date: str | None
    next_due: str | None
    overdue: int
    days_until_next: int | None
    note: str | None


@dataclass(frozen=True)
class BriefPendingItem:
    title: str
    description: str
    done: bool


@dataclass(frozen=True)
class BriefMood:
    summary: str
    reason: str | None


@dataclass(frozen=True)
class BriefMeal:
    tag: str
    what: str
    occurred_at: str


@dataclass(frozen=True)
class BriefMedication:
    medication_id: str
    name: str
    action: str
    occurred_at: str | None
    recorded_at: str
    dose: str | None
    note: str | None


@dataclass(frozen=True)
class BriefOuting:
    place: str
    purpose: str | None
    left_at: str
    returned_at: str | None


@dataclass(frozen=True)
class BriefTodo:
    title: str
    description: str
    done: bool


@dataclass(frozen=True)
class BriefWorkPlanItem:
    project_title: str
    milestone_title: str
    task_title: str
    task_status: str


@dataclass(frozen=True)
class BriefWorkSession:
    task_title: str
    checked_in_at: str
    checked_out_at: str | None


@dataclass(frozen=True)
class BriefScheduleEvent:
    title: str
    starts_at: str
    ends_at: str


@dataclass(frozen=True)
class BriefLifeDay:
    date: str
    wake_at: str
    sleep_at: str | None
    workday_capacity: float | int | None
    status: str
    mood: BriefMood | None
    meals: tuple[BriefMeal, ...]
    medications: tuple[BriefMedication, ...]
    outings: tuple[BriefOuting, ...]
    todos: tuple[BriefTodo, ...]
    work_plan: tuple[BriefWorkPlanItem, ...]
    open_work_session: BriefWorkSession | None
    recorded_work_minutes: int | None
    external_schedule: tuple[BriefScheduleEvent, ...]


@dataclass(frozen=True)
class BriefProjectTask:
    title: str
    status: str


@dataclass(frozen=True)
class BriefProjectMilestone:
    title: str
    remaining_effort: float | int
    calendar_time: str
    open_tasks: tuple[BriefProjectTask, ...]


@dataclass(frozen=True)
class BriefProject:
    title: str
    status: str
    waiting_on: str | None
    pause_reason: str | None
    current_milestone: BriefProjectMilestone | None
    deadline_time: str


@dataclass(frozen=True)
class BriefCalendarStatus:
    status: str
    fetched_at: str | None
    error: str | None


@dataclass(frozen=True)
class BriefProjection:
    """Structured, read-only input shared by brief.md and trusted group context.

    Only fields already intended for the generated brief are copied here.
    Raw day notes, project decisions, task notes, message logs, private spark,
    credentials, and unrelated repository files are never read into this DTO.
    """

    generated_at: str
    medical: BriefMedical | None
    pending_items: tuple[BriefPendingItem, ...]
    current_day: BriefLifeDay | None
    projects: tuple[BriefProject, ...]
    calendar: BriefCalendarStatus


def build_brief_projection(
    *,
    project_docs: Iterable[tuple[Path, dict[str, Any]]],
    day_docs: Iterable[tuple[Path, dict[str, Any]]],
    calendar_index: dict[str, Any],
    medical: dict[str, Any] | None = None,
    pending: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> BriefProjection:
    project_docs = list(project_docs)
    day_docs = list(day_docs)
    project_values = [project for _, project in project_docs]
    projects_by_id = {
        str(project.get("project_id")): project
        for project in project_values
        if project.get("project_id") is not None
    }

    active_days = [day for _, day in day_docs if day.get("status") == "active"]
    current_day = (
        _build_life_day(active_days[0], projects_by_id)
        if active_days
        else None
    )

    visible_projects = tuple(
        _build_project(project, calendar_index)
        for project in sorted(
            (
                item
                for item in project_values
                if item.get("status") in {"draft", "active", "waiting", "paused"}
            ),
            key=lambda item: str(item.get("title", "")).casefold(),
        )
    )

    source = calendar_index.get("source", {}) if isinstance(calendar_index, dict) else {}
    calendar = BriefCalendarStatus(
        status=str(source.get("status", "unknown")),
        fetched_at=_optional_str(source.get("fetched_at")),
        error=_optional_str(source.get("error")),
    )

    return BriefProjection(
        generated_at=generated_at or now_iso(),
        medical=_build_medical(medical or {}),
        pending_items=tuple(
            BriefPendingItem(
                title=str(item.get("title", "")),
                description=str(item.get("description", "")),
                done=bool(item.get("done")),
            )
            for item in (pending or {}).get("items", [])
        ),
        current_day=current_day,
        projects=visible_projects,
        calendar=calendar,
    )


def load_brief_projection(
    paths: NeoPaths,
    *,
    generated_at: str | None = None,
) -> BriefProjection:
    """Load canonical documents and construct the shared brief projection."""

    repo = Repository(paths)
    project_docs = [(location.path, location.data) for location in repo.load_projects()]
    day_docs = [(path, read_json(path)) for path in repo.day_files()]
    calendar = (
        read_json(paths.calendar_index)
        if paths.calendar_index.is_file()
        else {"source": {"status": "unknown"}, "events": {}}
    )
    medical = read_json(paths.medical_file) if paths.medical_file.is_file() else {}
    pending = read_json(paths.pending_file) if paths.pending_file.is_file() else {}
    return build_brief_projection(
        project_docs=project_docs,
        day_docs=day_docs,
        calendar_index=calendar,
        medical=medical,
        pending=pending,
        generated_at=generated_at,
    )


def brief_projection_to_dict(projection: BriefProjection) -> dict[str, Any]:
    """Return a JSON-serializable representation without persisting a file."""

    return asdict(projection)


def _build_medical(raw: dict[str, Any]) -> BriefMedical | None:
    if not raw or not raw.get("records"):
        return None
    from .domain.medical import with_status

    recurring = [item for item in with_status(raw)["records"] if "status" in item]
    if not recurring:
        return None
    item = min(recurring, key=lambda value: value["status"]["days_until_next"])
    status = item["status"]
    return BriefMedical(
        days_since=_optional_int(status.get("days_since")),
        last_date=_optional_str(item.get("last_date")),
        next_due=_optional_str(status.get("next_due")),
        overdue=_optional_int(status.get("overdue")) or 0,
        days_until_next=_optional_int(status.get("days_until_next")),
        note=None,
    )


def _build_life_day(
    day: dict[str, Any],
    projects_by_id: dict[str, dict[str, Any]],
) -> BriefLifeDay:
    sessions = list(day.get("work_sessions", []))
    open_sessions = [session for session in sessions if session.get("checked_out_at") is None]
    open_session = None
    if open_sessions:
        session = open_sessions[0]
        open_session = BriefWorkSession(
            task_title=str(session.get("task_title_snapshot", "")),
            checked_in_at=str(session.get("checked_in_at", "")),
            checked_out_at=_optional_str(session.get("checked_out_at")),
        )

    work_plan = tuple(
        BriefWorkPlanItem(
            project_title=str(item.get("project_title_snapshot", "")),
            milestone_title=str(item.get("milestone_title_snapshot", "")),
            task_title=str(item.get("task_title_snapshot", "")),
            task_status=_task_status(projects_by_id, str(item.get("task_id", ""))),
        )
        for item in day.get("work_plan", [])
    )

    mood_raw = day.get("mood")
    mood = (
        BriefMood(
            summary=str(mood_raw.get("summary", "")),
            reason=_optional_str(mood_raw.get("reason")),
        )
        if isinstance(mood_raw, dict)
        else None
    )

    return BriefLifeDay(
        date=str(day.get("date", "")),
        wake_at=str(day.get("wake_at", "")),
        sleep_at=_optional_str(day.get("sleep_at")),
        workday_capacity=day.get("workday_capacity"),
        status=str(day.get("status", "active")),
        mood=mood,
        meals=tuple(
            BriefMeal(
                tag=str(item.get("tag", "")),
                what=str(item.get("what", "")),
                occurred_at=str(item.get("occurred_at", "")),
            )
            for item in day.get("meals", [])
        ),
        medications=tuple(
            BriefMedication(
                medication_id=str(item.get("medication_id", "")),
                name=str(item.get("name", "")),
                action=str(item.get("action", "taken")),
                occurred_at=_optional_str(item.get("occurred_at")),
                recorded_at=str(item.get("recorded_at", "")),
                dose=_optional_str(item.get("dose")),
                note=_optional_str(item.get("note")),
            )
            for item in day.get("medications", [])
        ),
        outings=tuple(
            BriefOuting(
                place=str(item.get("place", "")),
                purpose=_optional_str(item.get("purpose")),
                left_at=str(item.get("left_at", "")),
                returned_at=_optional_str(item.get("returned_at")),
            )
            for item in day.get("outings", [])
        ),
        todos=tuple(
            BriefTodo(
                title=str(item.get("title", "")),
                description=str(item.get("description", "")),
                done=bool(item.get("done")),
            )
            for item in day.get("todolist", [])
        ),
        work_plan=work_plan,
        open_work_session=open_session,
        recorded_work_minutes=(sum(_session_minutes(session) for session in sessions) if sessions else None),
        external_schedule=tuple(
            BriefScheduleEvent(
                title=str(item.get("title", "")),
                starts_at=str(item.get("starts_at", "")),
                ends_at=str(item.get("ends_at", "")),
            )
            for item in day.get("external_schedule_snapshot", [])
        ),
    )


def _build_project(
    project: dict[str, Any],
    calendar_index: dict[str, Any],
) -> BriefProject:
    milestone_raw = _current_milestone(project)
    milestone = None
    if milestone_raw is not None:
        milestone = BriefProjectMilestone(
            title=str(milestone_raw.get("title", "")),
            remaining_effort=milestone_raw.get("remaining_effort", 0),
            calendar_time=_calendar_event_time(
                calendar_index,
                _optional_str(milestone_raw.get("calendar_event_id")),
            ),
            open_tasks=tuple(
                BriefProjectTask(
                    title=str(task.get("title", "")),
                    status=str(task.get("status", "todo")),
                )
                for task in milestone_raw.get("tasks", [])
                if task.get("status") not in {"done", "cancelled"}
            ),
        )

    waiting = project.get("waiting")
    pause = project.get("pause")
    return BriefProject(
        title=str(project.get("title", "")),
        status=str(project.get("status", "draft")),
        waiting_on=(
            _optional_str(waiting.get("on"))
            if isinstance(waiting, dict)
            else None
        ),
        pause_reason=(
            _optional_str(pause.get("reason"))
            if isinstance(pause, dict)
            else None
        ),
        current_milestone=milestone,
        deadline_time=_calendar_event_time(
            calendar_index,
            _optional_str(project.get("deadline_calendar_event_id")),
        ),
    )


def _current_milestone(project: dict[str, Any]) -> dict[str, Any] | None:
    milestone_id = project.get("current_milestone_id")
    if milestone_id is None:
        return None
    return next(
        (
            item
            for item in project.get("milestones", [])
            if item.get("milestone_id") == milestone_id
        ),
        None,
    )


def _task_status(
    projects_by_id: dict[str, dict[str, Any]],
    task_id: str,
) -> str:
    for project in projects_by_id.values():
        for milestone in project.get("milestones", []):
            for task in milestone.get("tasks", []):
                if str(task.get("task_id", "")) == task_id:
                    return str(task.get("status", "missing"))
    return "missing"


def _calendar_event_time(
    calendar_index: dict[str, Any],
    event_id: str | None,
) -> str:
    if not event_id:
        return "연결 안 됨"
    events = calendar_index.get("events", {}) if isinstance(calendar_index, dict) else {}
    event = events.get(event_id) if isinstance(events, dict) else None
    if not isinstance(event, dict):
        source = calendar_index.get("source", {}) if isinstance(calendar_index, dict) else {}
        status = source.get("status") if isinstance(source, dict) else None
        return "확인 불가" if status != "available" else "연결된 이벤트를 찾지 못함"
    return str(event.get("starts_at", ""))


def _session_minutes(session: dict[str, Any]) -> int:
    checked_out = session.get("checked_out_at")
    checked_in = session.get("checked_in_at")
    if not checked_out or not checked_in:
        return 0
    try:
        start = datetime.fromisoformat(str(checked_in))
        end = datetime.fromisoformat(str(checked_out))
    except ValueError:
        return 0
    return max(0, round((end - start).total_seconds() / 60))


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None
