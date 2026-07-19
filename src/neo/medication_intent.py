from __future__ import annotations

from .errors import ValidationError
from .utils import parse_datetime

_EXPLICIT_MUTATION_CUES = (
    "기록해줘",
    "다시 추가해줘",
    "추가해줘",
    "지워줘",
    "삭제해줘",
    "정정해줘",
    "수정해줘",
)
_CONTRADICTION_CUES = (
    "맞잖아",
    "뭔 소리야",
    "무슨 소리야",
    "이상한데",
)
_QUERY_CUES = (
    "언제",
    "마지막",
    "오늘",
    "기록",
    "먹었어?",
    "했더라",
    "남아 있어",
    "남아있어",
)


def classify_medication_intent(text: str) -> str:
    """Classify the medication boundary before any tool is selected.

    This is deliberately conservative: contradiction is a re-query signal,
    never an implicit add/remove/correct approval.
    """

    normalized = " ".join(text.strip().casefold().split())
    if any(cue in normalized for cue in _EXPLICIT_MUTATION_CUES):
        if "삭제" in normalized or "지워" in normalized:
            return "explicit_remove"
        if "정정" in normalized or "수정" in normalized:
            return "explicit_correct"
        return "explicit_add"
    if any(cue in normalized for cue in _CONTRADICTION_CUES):
        return "contradiction_requery"
    if any(cue in normalized for cue in _QUERY_CUES):
        return "read_only_query"
    return "unknown"


def medication_mutation_requires_confirmation(intent: str, candidate_count: int) -> bool:
    """Require a second confirmation when a destructive target is ambiguous."""

    if candidate_count < 0:
        raise ValidationError("candidate_count must not be negative")
    if intent not in {"explicit_remove", "explicit_correct"}:
        return False
    return candidate_count != 1


def reply_timestamp_relation(
    occurred_at: str | None,
    reply_timestamp: str | None,
) -> str:
    """Describe reply-time evidence without treating it as a medication mutation."""

    if occurred_at is None:
        return "occurred_time_unknown"
    if reply_timestamp is None:
        return "no_reply_timestamp"
    occurred = parse_datetime(occurred_at)
    replied = parse_datetime(reply_timestamp)
    if occurred == replied:
        return "same_instant"
    return "conflict_requires_confirmation"
