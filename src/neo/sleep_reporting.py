"""Deterministic sleep-report routing and recording boundary.

The life-day protocol owns the meaning of sleep.  This module only makes the
ordering explicit for runtimes that need to route a message before asking
follow-up questions.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal
from zoneinfo import ZoneInfo


_SEOUL = ZoneInfo("Asia/Seoul")
SleepIntent = Literal["explicit", "not_explicit"]
SleepAction = Literal["record_sleep", "acknowledge_sleep", "ask_follow_ups"]
NapIntent = Literal["explicit", "not_explicit"]
NapAction = Literal["record_nap", "acknowledge_nap"]


@dataclass(frozen=True)
class SleepTurnPlan:
    intent: SleepIntent
    actions: tuple[SleepAction, ...]

    @property
    def should_record(self) -> bool:
        return self.intent == "explicit"


@dataclass(frozen=True)
class NapTurnPlan:
    intent: NapIntent
    actions: tuple[NapAction, ...]

    @property
    def should_record(self) -> bool:
        return self.intent == "explicit"


@dataclass(frozen=True)
class NapRecordResult:
    success: bool
    occurred_at: str | None = None
    nap_id: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class SleepRecordResult:
    success: bool
    occurred_at: str | None = None
    error: str | None = None


def _normalized_text(text: str | None) -> str:
    return " ".join(str(text or "").casefold().split()).strip()


def classify_sleep_intent(text: str | None) -> SleepIntent:
    """Recognize only a clear sleep report, not sleepiness or a question."""

    value = _normalized_text(text)
    if not value or "?" in value or "？" in value:
        return "not_explicit"

    explicit_phrases = (
        "잘게",
        "잘게요",
        "잘 거야",
        "잘 거예요",
        "자러 갈게",
        "자러 갈게요",
        "자러 갈 거야",
        "자러 갈 거예요",
        "이제 잔다",
        "이제 잘게",
        "이제 잘게요",
        "이제 잘 거야",
        "이제 잘 거예요",
        "잠들게",
        "잠들게요",
        "잠들 거야",
        "잠들 거예요",
    )
    return "explicit" if any(phrase in value for phrase in explicit_phrases) else "not_explicit"


def classify_nap_intent(text: str | None) -> NapIntent:
    """Recognize naps only when the message explicitly contains 낮잠."""
    value = _normalized_text(text)
    if not value or "?" in value or "？" in value or "낮잠" not in value:
        return "not_explicit"
    nap_phrases = ("낮잠잔다", "낮잠 잘게", "낮잠 잘 거야", "낮잠 자러", "낮잠 잠들")
    return "explicit" if any(phrase in value for phrase in nap_phrases) else "not_explicit"


def plan_nap_turn(text: str | None) -> NapTurnPlan:
    if classify_nap_intent(text) != "explicit":
        return NapTurnPlan("not_explicit", ())
    return NapTurnPlan("explicit", ("record_nap", "acknowledge_nap"))


def plan_sleep_turn(text: str | None) -> SleepTurnPlan:
    """Return the only permitted order for an explicit sleep report."""

    if classify_sleep_intent(text) != "explicit":
        return SleepTurnPlan("not_explicit", ())
    return SleepTurnPlan(
        "explicit",
        ("record_sleep", "acknowledge_sleep", "ask_follow_ups"),
    )


def normalize_received_at(value: object) -> str | None:
    """Normalize a Telegram message timestamp to an explicit Seoul ISO time."""

    if not isinstance(value, datetime):
        return None
    timestamp = value
    if timestamp.tzinfo is None:
        # python-telegram-bot supplies UTC timestamps; fail closed only for a
        # missing/non-datetime value, not for the documented naive fixture form.
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(_SEOUL).replace(microsecond=0).isoformat()


def _safe_env(root: Path) -> dict[str, str]:
    env = {key: os.environ[key] for key in ("HOME", "PATH", "TZ") if os.environ.get(key)}
    env["TZ"] = "Asia/Seoul"
    env["NEO_ROOT"] = str(root)
    return env


def record_nap(
    root: Path,
    received_at: object,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> NapRecordResult:
    occurred_at = normalize_received_at(received_at)
    if occurred_at is None:
        return NapRecordResult(False, error="message timestamp is missing or invalid")
    executable = root / ".venv" / "bin" / "neoctl"
    if not executable.is_file():
        return NapRecordResult(False, occurred_at, error="neoctl executable is unavailable")
    try:
        completed = runner(
            [str(executable), "--json", "day", "nap", "go", "--at", occurred_at],
            cwd=root,
            env=_safe_env(root),
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return NapRecordResult(False, occurred_at, error=f"neoctl failed: {exc.__class__.__name__}")
    if completed.returncode != 0:
        return NapRecordResult(False, occurred_at, error="neoctl returned a failure")
    try:
        payload = json.loads(completed.stdout or "")
    except (TypeError, ValueError):
        return NapRecordResult(False, occurred_at, error="neoctl returned invalid JSON")
    if not isinstance(payload, dict) or payload.get("ok") is False:
        return NapRecordResult(False, occurred_at, error="neoctl did not confirm the nap record")
    return NapRecordResult(True, occurred_at, payload.get("nap_id"))


def record_sleep(
    root: Path,
    received_at: object,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> SleepRecordResult:
    """Record one explicit sleep report, without claiming success on failure."""

    occurred_at = normalize_received_at(received_at)
    if occurred_at is None:
        return SleepRecordResult(False, error="message timestamp is missing or invalid")

    executable = root / ".venv" / "bin" / "neoctl"
    if not executable.is_file():
        return SleepRecordResult(False, occurred_at, "neoctl executable is unavailable")

    try:
        completed = runner(
            [str(executable), "--json", "day", "sleep", "--at", occurred_at],
            cwd=root,
            env=_safe_env(root),
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return SleepRecordResult(False, occurred_at, f"neoctl failed: {exc.__class__.__name__}")

    if completed.returncode != 0:
        return SleepRecordResult(False, occurred_at, "neoctl returned a failure")
    try:
        payload = json.loads(completed.stdout or "")
    except (TypeError, ValueError):
        return SleepRecordResult(False, occurred_at, "neoctl returned invalid JSON")
    if not isinstance(payload, dict) or payload.get("ok") is False or payload.get("success") is False:
        return SleepRecordResult(False, occurred_at, "neoctl did not confirm the sleep record")
    return SleepRecordResult(True, occurred_at)
