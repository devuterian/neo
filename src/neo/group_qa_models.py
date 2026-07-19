from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


GroupTopic = Literal[
    "wake",
    "sleep",
    "meal",
    "outing",
    "work_now",
    "work_time",
    "completed_today",
    "todo_today",
    "availability",
    "light_status",
    "medical",
    "brief",
    "spark_sensitive",
    "sensitive",
    "unsupported",
]


@dataclass(frozen=True)
class GroupQASettings:
    enabled: bool
    allowed_group_chats: set[str]
    allowed_topics: set[str]
    deny_sensitive: bool
    max_answer_chars: int
    public_project_allowlist: set[str]
    detail_level: Literal["safe", "trusted"]
    brief_max_chars: int
    model_enabled: bool
    session_mode: Literal["per_chat"]
    model_session_idle_minutes: int
    model_override: str | None
    reasoning_effort: str | None


@dataclass(frozen=True)
class TrustedGroupBriefSummary:
    generated_at: str | None
    current_life_day: str | None
    sections: tuple[tuple[str, tuple[str, ...]], ...]
    open_pending_count: int
    open_medication_count: int
    open_project_count: int


@dataclass(frozen=True)
class GroupQuestionClassification:
    category: GroupTopic
    allowed: bool
    reason: str


@dataclass(frozen=True)
class GroupQAResponse:
    """Portable group-Q&A reply with an optional structured rich payload."""

    text: str
    rich: dict[str, Any] | None = None


@dataclass(frozen=True)
class GroupPublicStatus:
    date: str | None
    wake_recorded: bool
    wake_time_bucket: str | None
    sleep_recorded: bool
    sleep_time_bucket: str | None
    meal_recorded: bool
    meal_public_items: tuple[str, ...]
    outing_recorded: bool
    outing_public_places: tuple[str, ...]
    has_ongoing_outing: bool
    is_working_now: bool
    work_time_buckets: tuple[str, ...]
    public_work_summary: str | None
    completed_count: int
    public_completed_items: tuple[str, ...]
    todo_count: int
    public_todo_items: tuple[str, ...]
    availability: Literal["busy", "maybe_available", "unknown"]
    light_status: Literal["working", "resting", "out", "unknown"]
    medical_available: bool = False
    medical_last_date: str | None = None
    medical_days_since: int | None = None
    medical_next_due: str | None = None
    medical_days_until_next: int | None = None
    medical_overdue: int | None = None
    trusted: bool = False
    wake_time: str | None = None
    sleep_time: str | None = None
    meal_details: tuple[tuple[str, str], ...] = ()
    work_session_details: tuple[str, ...] = ()
    today_wake_at: str | None = None
    today_wake_date: str | None = None
    today_wake_is_same_local_date: bool = False
    latest_wake_at: str | None = None
    latest_wake_date: str | None = None
    latest_wake_source_day: str | None = None
    latest_sleep_at: str | None = None
    latest_sleep_date: str | None = None
    latest_sleep_source_day: str | None = None
    has_ongoing_nap: bool = False
