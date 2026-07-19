from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from neo.domain.days import add_nap, create_day, finish_nap, update_nap
from neo.group_qa_policy import classify_group_question
from neo.group_qa_projection import build_group_public_status
from neo.group_qa_renderer import answer_group_question
from neo.paths import NeoPaths
from neo.sleep_reporting import classify_nap_intent, plan_nap_turn


def test_nap_intent_requires_explicit_nap_word() -> None:
    assert classify_nap_intent("낮잠잔다") == "explicit"
    assert plan_nap_turn("낮잠 잘게").should_record
    assert classify_nap_intent("나 잘게") == "not_explicit"


def test_day_supports_multiple_naps_with_start_and_end() -> None:
    day = create_day("2026-07-15T10:00:00+09:00")
    day, first_id = add_nap(day, started_at="2026-07-15T14:00:00+09:00")
    day = finish_nap(day, first_id, "2026-07-15T15:30:00+09:00")
    day, second_id = add_nap(day, started_at="2026-07-15T19:00:00+09:00")

    assert len(day["naps"]) == 2
    assert day["naps"][0]["ended_at"] == "2026-07-15T15:30:00+09:00"
    assert day["naps"][1]["nap_id"] == second_id
    assert day["naps"][1]["ended_at"] is None


def test_trusted_group_reports_ongoing_nap_as_nap(tmp_path: Path) -> None:
    (tmp_path / "data/days/2026").mkdir(parents=True)
    day = create_day("2026-07-15T10:00:00+09:00")
    day, _ = add_nap(day, started_at="2026-07-15T14:00:00+09:00")
    (tmp_path / "data/days/2026/2026-07-15.json").write_text(
        json.dumps(day, ensure_ascii=False), encoding="utf-8"
    )
    (tmp_path / "data/indexes").mkdir(parents=True)
    (tmp_path / "data/indexes/current.json").write_text(
        json.dumps({"current_day": {"path": "data/days/2026/2026-07-15.json"}}),
        encoding="utf-8",
    )

    status = build_group_public_status(
        NeoPaths(tmp_path),
        now=datetime(2026, 7, 15, 14, 30, tzinfo=ZoneInfo("Asia/Seoul")),
        detail_level="trusted",
    )
    classification = classify_group_question("자냐고 물어봐도 돼?", {"sleep"})

    assert status.has_ongoing_nap
    assert answer_group_question(classification, status) == "낮잠잔다고 기록돼 있어."


def test_nap_can_be_updated() -> None:
    day = create_day("2026-07-15T10:00:00+09:00")
    day, nap_id = add_nap(day, started_at="2026-07-15T14:00:00+09:00")
    day = finish_nap(day, nap_id, "2026-07-15T15:00:00+09:00")

    updated = update_nap(
        day,
        nap_id,
        started_at="2026-07-15T13:45:00+09:00",
        ended_at="2026-07-15T15:10:00+09:00",
    )

    assert updated["naps"][0]["started_at"] == "2026-07-15T13:45:00+09:00"
    assert updated["naps"][0]["ended_at"] == "2026-07-15T15:10:00+09:00"
