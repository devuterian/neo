from __future__ import annotations

from typing import Mapping

from .group_qa_models import GroupQASettings


DEFAULT_TOPICS = {
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
}
_TRUE = {"true", "1", "yes", "on"}
_VALID_REASONING_EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh", "max"}


def _csv(value: str | None) -> set[str]:
    return {item.strip() for item in (value or "").split(",") if item.strip()}


def normalize_chat_id(value: str | int) -> str:
    """Normalize Telegram integer IDs without changing negative IDs."""

    return str(value).strip()


def _bounded_int(value: str | None, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value if value is not None else default)
        if not minimum <= parsed <= maximum:
            raise ValueError
        return parsed
    except (TypeError, ValueError):
        return default


def parse_group_qa_settings(env: Mapping[str, str]) -> GroupQASettings:
    primary = env.get("TELEGRAM_ALLOWED_GROUP_CHATS")
    raw_groups = primary if primary is not None and primary.strip() else env.get("TELEGRAM_GROUP_ALLOWED_CHATS")
    detail_level = (
        "trusted"
        if env.get("TELEGRAM_GROUP_QA_DETAIL_LEVEL", "safe").strip().casefold() == "trusted"
        else "safe"
    )
    raw_effort = env.get("TELEGRAM_GROUP_QA_REASONING_EFFORT", "").strip().lower()
    return GroupQASettings(
        enabled=env.get("TELEGRAM_GROUP_QA_ENABLED", "").strip().lower() in _TRUE,
        allowed_group_chats={normalize_chat_id(value) for value in _csv(raw_groups)},
        allowed_topics=_csv(env.get("TELEGRAM_GROUP_QA_ALLOWED_TOPICS")) or set(DEFAULT_TOPICS),
        # Retained for configuration compatibility. Sensitive data is always denied.
        deny_sensitive=env.get("TELEGRAM_GROUP_QA_DENY_SENSITIVE", "true").strip().lower() in _TRUE,
        max_answer_chars=_bounded_int(
            env.get("TELEGRAM_GROUP_QA_MAX_ANSWER_CHARS"), default=300, minimum=1, maximum=2000
        ),
        public_project_allowlist=_csv(env.get("TELEGRAM_GROUP_QA_PUBLIC_PROJECT_ALLOWLIST")),
        detail_level=detail_level,
        brief_max_chars=_bounded_int(
            env.get("TELEGRAM_GROUP_QA_BRIEF_MAX_CHARS"), default=700, minimum=1, maximum=4000
        ),
        model_enabled=env.get("TELEGRAM_GROUP_QA_MODEL_ENABLED", "false").strip().lower() in _TRUE,
        session_mode="per_chat",
        model_session_idle_minutes=_bounded_int(
            env.get("TELEGRAM_GROUP_QA_MODEL_SESSION_IDLE_MINUTES"),
            default=120,
            minimum=1,
            maximum=1440,
        ),
        model_override=env.get("TELEGRAM_GROUP_QA_MODEL", "").strip() or None,
        reasoning_effort=raw_effort if raw_effort in _VALID_REASONING_EFFORTS else None,
    )
