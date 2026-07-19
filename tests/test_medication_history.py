from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import patch

from helpers import TempRepository, run_cli
from neo.domain.days import create_day
from neo.cli_days import handle_day
from neo.utils import new_uuid


def _write_day(repo: TempRepository, wake_at: str, medications: list[dict]) -> Path:
    day = create_day(wake_at)
    day["medications"] = medications
    path = repo.paths.days / day["date"][:4] / f"{day['date']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(day, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _event(
    name: str,
    action: str,
    occurred_at: str | None,
    recorded_at: str = "2026-07-12T12:00:00+09:00",
    *,
    note: str | None = None,
) -> dict:
    return {
        "medication_id": new_uuid(),
        "name": name,
        "action": action,
        "occurred_at": occurred_at,
        "recorded_at": recorded_at,
        "dose": None,
        "note": note,
    }


def _history(repo: TempRepository, *args: str) -> list[dict]:
    result = run_cli(repo.root, "--json", "day", "med", "history", *args)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["medications"]


def test_cross_midnight_uses_actual_date_not_life_day_date() -> None:
    repo = TempRepository(Path(__file__).resolve().parents[1])
    try:
        _write_day(
            repo,
            "2026-07-11T23:00:00+09:00",
            [_event("약 A", "taken", "2026-07-12T07:03:00+09:00")],
        )

        event = _history(repo, "--name", "  약 A  ")[0]

        assert event["occurred_at"] == "2026-07-12T07:03:00+09:00"
        assert event["actual_date"] == "2026-07-12"
        assert event["life_day_date"] == "2026-07-11"
        assert event["actual_date"] != event["life_day_date"]
    finally:
        repo.close()


def test_latest_is_selected_by_occurred_at_across_life_days() -> None:
    repo = TempRepository(Path(__file__).resolve().parents[1])
    try:
        newer_actual_event = _event("약 A", "taken", "2026-07-12T07:03:00+09:00")
        older_actual_event = _event("약 A", "taken", "2026-07-11T23:50:00+09:00")
        _write_day(repo, "2026-07-12T08:00:00+09:00", [older_actual_event])
        _write_day(repo, "2026-07-11T08:00:00+09:00", [newer_actual_event])

        events = _history(repo, "--name", "약 A", "--limit", "1")

        assert len(events) == 1
        assert events[0]["medication_id"] == newer_actual_event["medication_id"]
        assert events[0]["life_day_date"] == "2026-07-11"
    finally:
        repo.close()


def test_repeated_events_in_one_life_day_are_all_preserved() -> None:
    repo = TempRepository(Path(__file__).resolve().parents[1])
    try:
        first = _event("약 B", "taken", "2026-07-12T10:00:00+09:00")
        second = _event("약 B", "taken", "2026-07-12T22:00:00+09:00")
        _write_day(repo, "2026-07-12T08:00:00+09:00", [first, second])

        events = _history(repo, "--name", "약 B")

        assert [event["medication_id"] for event in events] == [
            second["medication_id"],
            first["medication_id"],
        ]
    finally:
        repo.close()


def test_action_filter_separates_skipped_from_taken() -> None:
    repo = TempRepository(Path(__file__).resolve().parents[1])
    try:
        _write_day(
            repo,
            "2026-07-12T08:00:00+09:00",
            [
                _event("약 B", "taken", "2026-07-12T10:00:00+09:00"),
                _event("약 B", "skipped", "2026-07-12T22:00:00+09:00", note="잊음"),
            ],
        )

        skipped = _history(repo, "--name", "약 B", "--action", "skipped")

        assert len(skipped) == 1
        assert skipped[0]["action"] == "skipped"
        assert skipped[0]["note"] == "잊음"
    finally:
        repo.close()


def test_unknown_occurred_at_is_not_filled_from_recorded_or_life_day_date() -> None:
    repo = TempRepository(Path(__file__).resolve().parents[1])
    try:
        _write_day(
            repo,
            "2026-07-11T23:00:00+09:00",
            [_event("약 A", "taken", None, "2026-07-12T07:04:00+09:00")],
        )

        event = _history(repo, "--name", "약 A")[0]

        assert event["occurred_at"] is None
        assert event["actual_date"] is None
        assert event["life_day_date"] == "2026-07-11"
    finally:
        repo.close()


def test_occurred_at_is_converted_to_seoul_date() -> None:
    repo = TempRepository(Path(__file__).resolve().parents[1])
    try:
        _write_day(
            repo,
            "2026-07-11T08:00:00+09:00",
            [_event("약 B", "taken", "2026-07-11T23:30:00Z")],
        )

        event = _history(repo, "--name", "약 B")[0]

        assert event["occurred_at"] == "2026-07-12T08:30:00+09:00"
        assert event["actual_date"] == "2026-07-12"
    finally:
        repo.close()


def test_history_is_read_only_and_does_not_call_workspace_commit() -> None:
    repo = TempRepository(Path(__file__).resolve().parents[1])
    try:
        _write_day(
            repo,
            "2026-07-12T08:00:00+09:00",
            [_event("약 A", "taken", "2026-07-12T09:00:00+09:00")],
        )
        before = {
            path.relative_to(repo.root): path.read_bytes()
            for path in repo.root.rglob("*")
            if path.is_file()
        }

        with patch("neo.cli_days.commit_workspace") as commit:
            result = handle_day(
                repo.paths,
                argparse.Namespace(
                    day_command="med",
                    med_command="history",
                    name="약 A",
                    action=None,
                    since=None,
                    until=None,
                    limit=None,
                ),
            )

        after = {
            path.relative_to(repo.root): path.read_bytes()
            for path in repo.root.rglob("*")
            if path.is_file()
        }
        assert result["medications"]
        assert before == after
        commit.assert_not_called()
    finally:
        repo.close()


def test_history_rejects_future_day_schema_without_writing() -> None:
    repo = TempRepository(Path(__file__).resolve().parents[1])
    try:
        path = _write_day(
            repo,
            "2026-07-12T08:00:00+09:00",
            [_event("약 A", "taken", "2026-07-12T09:00:00+09:00")],
        )
        day = json.loads(path.read_text(encoding="utf-8"))
        day["schema_version"] = 3
        path.write_text(json.dumps(day, ensure_ascii=False), encoding="utf-8")

        result = run_cli(repo.root, "--json", "day", "med", "history")

        assert result.returncode == 2
        assert "schema_version" in result.stderr
        assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 3
    finally:
        repo.close()
