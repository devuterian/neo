from __future__ import annotations
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from neo.sleep_reporting import (
    classify_sleep_intent,
    plan_sleep_turn,
    record_sleep,
)


def test_explicit_sleep_reports_record_before_followups() -> None:
    plan = plan_sleep_turn("나 이제 잘게")
    assert plan.should_record
    assert plan.actions == ("record_sleep", "acknowledge_sleep", "ask_follow_ups")


def test_sleepiness_or_question_is_not_a_sleep_report() -> None:
    for text in ("졸리다", "잘까?", "이제 잘게?", "누워야겠다"):
        assert classify_sleep_intent(text) == "not_explicit"
        assert not plan_sleep_turn(text).should_record


def test_record_sleep_uses_message_time_and_calls_neoctl_once(tmp_path: Path) -> None:
    executable = tmp_path / ".venv" / "bin" / "neoctl"
    executable.parent.mkdir(parents=True)
    executable.write_text("", encoding="utf-8")
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def runner(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args[0], 0, '{"ok": true}', "")

    result = record_sleep(
        tmp_path,
        datetime(2026, 7, 14, 14, 3, 0, tzinfo=timezone.utc),
        runner=runner,
    )

    assert result.success
    assert result.occurred_at == "2026-07-14T23:03:00+09:00"
    assert len(calls) == 1
    assert calls[0][0][0][1:] == ["--json", "day", "sleep", "--at", "2026-07-14T23:03:00+09:00"]


def test_record_sleep_failure_does_not_claim_success(tmp_path: Path) -> None:
    executable = tmp_path / ".venv" / "bin" / "neoctl"
    executable.parent.mkdir(parents=True)
    executable.write_text("", encoding="utf-8")

    def runner(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args[0], 1, "", "failed")

    result = record_sleep(tmp_path, datetime(2026, 7, 14, 23, 3, tzinfo=ZoneInfo("Asia/Seoul")), runner=runner)

    assert not result.success
    assert result.occurred_at == "2026-07-14T23:03:00+09:00"
    assert result.error == "neoctl returned a failure"
