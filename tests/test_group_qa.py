from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


_FIXTURE_NOW = datetime(2026, 7, 10, 12, 0, tzinfo=ZoneInfo("Asia/Seoul"))

from neo.group_qa import (
    GroupPublicStatus, answer_group_brief, answer_group_question, build_group_brief_response, build_group_public_status,
    build_trusted_group_model_context, classify_group_question, is_group_private_spark_question, normalize_chat_id, parse_group_qa_settings,
)
from neo.paths import NeoPaths


def _status() -> GroupPublicStatus:
    return GroupPublicStatus("2026-07-10", True, "morning", False, None, True, (), False, (), False, True, ("afternoon",), None, 1, (), 1, (), "busy", "working")


def test_settings_defaults_and_aliases():
    settings = parse_group_qa_settings({})
    assert settings.enabled is False and settings.max_answer_chars == 300 and settings.detail_level == "safe" and settings.brief_max_chars == 700
    assert settings.model_enabled is False and settings.session_mode == "per_chat" and settings.model_session_idle_minutes == 120
    assert parse_group_qa_settings({"TELEGRAM_ALLOWED_GROUP_CHATS": "-100, 42"}).allowed_group_chats == {"-100", "42"}
    assert parse_group_qa_settings({"TELEGRAM_GROUP_ALLOWED_CHATS": "-100"}).allowed_group_chats == {"-100"}
    assert normalize_chat_id(-100123) == "-100123" and normalize_chat_id(" -100 ") == "-100"


def test_model_session_settings_and_private_spark_prefilter():
    assert parse_group_qa_settings({"TELEGRAM_GROUP_QA_MODEL_SESSION_IDLE_MINUTES": "0"}).model_session_idle_minutes == 120
    assert parse_group_qa_settings({"TELEGRAM_GROUP_QA_MODEL_SESSION_IDLE_MINUTES": "1441"}).model_session_idle_minutes == 120
    assert parse_group_qa_settings({"TELEGRAM_GROUP_QA_MODEL_SESSION_IDLE_MINUTES": "30", "TELEGRAM_GROUP_QA_MODEL_ENABLED": "true"}).model_session_idle_minutes == 30
    assert is_group_private_spark_question("spark 마지막 시각 알려줘")
    assert is_group_private_spark_question("data/private/spark/2026")
    assert not is_group_private_spark_question("주사 며칠 됐어?")


def test_group_model_override_and_reasoning_effort_settings():
    # Defaults: no override
    s = parse_group_qa_settings({})
    assert s.model_override is None and s.reasoning_effort is None
    # Model override from env
    s = parse_group_qa_settings({"TELEGRAM_GROUP_QA_MODEL": "gpt-5.6-luna"})
    assert s.model_override == "gpt-5.6-luna" and s.reasoning_effort is None
    # Reasoning effort from env
    s = parse_group_qa_settings({"TELEGRAM_GROUP_QA_REASONING_EFFORT": "low"})
    assert s.model_override is None and s.reasoning_effort == "low"
    # Both together
    s = parse_group_qa_settings({"TELEGRAM_GROUP_QA_MODEL": "gpt-5.6-luna", "TELEGRAM_GROUP_QA_REASONING_EFFORT": "low"})
    assert s.model_override == "gpt-5.6-luna" and s.reasoning_effort == "low"
    # Invalid effort is ignored
    s = parse_group_qa_settings({"TELEGRAM_GROUP_QA_REASONING_EFFORT": "turbo"})
    assert s.reasoning_effort is None
    # Empty model string is None
    s = parse_group_qa_settings({"TELEGRAM_GROUP_QA_MODEL": "  "})
    assert s.model_override is None
    # All valid effort levels
    for level in ("none", "minimal", "low", "medium", "high", "xhigh", "max"):
        s = parse_group_qa_settings({"TELEGRAM_GROUP_QA_REASONING_EFFORT": level})
        assert s.reasoning_effort == level, f"Expected {level} but got {s.reasoning_effort}"


def test_classification_priority_and_topics():
    assert classify_group_question("오늘 일어났어?").category == "wake"
    assert classify_group_question("오늘 잤어?").category == "sleep"
    assert classify_group_question("밥 먹었어?").category == "meal"
    assert classify_group_question("외출했어?").category == "outing"
    assert classify_group_question("지금 작업 중이야?").category == "work_now"
    assert classify_group_question("언제 작업했어?").category == "work_time"
    assert classify_group_question("오늘 끝낸 일?").category == "completed_today"
    assert classify_group_question("오늘 할 일?").category == "todo_today"
    assert classify_group_question("연락해도 돼?").category == "availability"
    assert classify_group_question("컨디션 상태?").category == "light_status"
    assert classify_group_question("병원 검진 며칠 됐어?", {"medical"}).category == "medical"
    assert classify_group_question("밥이랑 private spark?").category == "spark_sensitive"
    assert classify_group_question("밥 먹었어? 병원은?", {"medical"}).category == "medical"
    assert classify_group_question("밥 먹었어?", {"wake"}).allowed is False


def test_answers_are_short_and_sensitive_is_refused():
    assert len(answer_group_question(classify_group_question("일어났어?"), _status(), max_chars=5)) <= 5
    assert "말할 수 없어" in answer_group_question(classify_group_question("spark 기록?"), _status())


def test_medical_is_trusted_only_and_uses_projection(tmp_path: Path):
    root = _projection_root(tmp_path)
    (root / "data/medical.json").write_text(json.dumps({
        "schema_version": 1,
        "records": [{"medical_id": "a", "provider": "Sample", "title": "Follow-up", "last_date": "2026-07-01", "cycle_days": 21, "kind": None, "note": "never expose this", "updated_at": "2026-07-01T00:00:00+09:00"}],
        "updated_at": "2026-07-01T00:00:00+09:00",
    }), encoding="utf-8")
    safe = build_group_public_status(NeoPaths(root), now=__import__("datetime").datetime(2026, 7, 10), detail_level="safe")
    trusted = build_group_public_status(NeoPaths(root), now=__import__("datetime").datetime(2026, 7, 10), detail_level="trusted")
    question = classify_group_question("medical 며칠째야?", {"medical"})
    assert not safe.medical_available and "trusted" in answer_group_question(question, safe)
    assert trusted.medical_days_since == 9 and trusted.medical_next_due == "2026-07-22"
    assert "9일 지났어" in answer_group_question(question, trusted)
    context = build_trusted_group_model_context(trusted)
    assert "medical=last_date=2026-07-01" in context and "never expose this" not in context


def test_status_context_does_not_hide_previous_life_day_sleep() -> None:
    status = replace(
        _status(),
        sleep_recorded=False,
        sleep_time=None,
        latest_sleep_at="2026-07-11T00:10:00+09:00",
        latest_sleep_date="2026-07-11",
        latest_sleep_source_day="2026-07-10",
    )

    context = build_trusted_group_model_context(status)

    assert "sleep_current_life_day=not_recorded" in context
    assert "sleep=recorded_in_history" in context
    assert "latest_sleep_source_day=2026-07-10" in context


def test_trusted_brief_excludes_notes_and_spark(tmp_path: Path):
    root = _projection_root(tmp_path)
    day_path = root / "data/days/2026/2026-07-10.json"
    day = json.loads(day_path.read_text(encoding="utf-8"))
    day.update({"wake_at": "2026-07-10T05:09:00+09:00", "meals": [{"occurred_at": "2026-07-10T05:30:00+09:00", "what": "라면"}], "notes": [{"text": "private spark"}]})
    day_path.write_text(json.dumps(day), encoding="utf-8")
    response = build_group_brief_response(build_group_public_status(NeoPaths(root), now=_FIXTURE_NOW, detail_level="trusted"))
    assert "05:09" in response.text and "05:30 라면" in response.text and "spark" not in response.text
    assert response.rich is not None and response.rich["kind"] == "group_qa_brief"
    assert "spark" not in repr(response.rich)


def test_brief_rich_payload_splits_meals_and_keeps_safe_fallback(tmp_path: Path):
    root = _projection_root(tmp_path)
    day_path = root / "data/days/2026/2026-07-10.json"
    day = json.loads(day_path.read_text(encoding="utf-8"))
    day.update({
        "wake_at": "2026-07-10T05:42:00+09:00",
        "meals": [
            {"occurred_at": "2026-07-10T07:40:00+09:00", "what": "카레 + 쌀밥 (엄마가 해줌)"},
            {"occurred_at": "2026-07-10T12:52:00+09:00", "what": "카레라이스"},
        ],
        "notes": [{"text": "private spark and a raw medical note"}],
    })
    day_path.write_text(json.dumps(day), encoding="utf-8")

    response = build_group_brief_response(build_group_public_status(NeoPaths(root), now=_FIXTURE_NOW, detail_level="trusted"))
    assert "🌤 오늘 브리프" in response.text and "• 07:40 카레 + 쌀밥" in response.text
    assert "  - 엄마가 해줌" in response.text
    assert response.rich is not None
    meal = response.rich["sections"][1]["rows"]
    assert meal == [
        {"time": "07:40", "text": "카레 + 쌀밥", "note": "엄마가 해줌"},
        {"time": "12:52", "text": "카레라이스"},
    ]
    assert "private spark" not in repr(response.rich)
    assert len(build_group_brief_response(build_group_public_status(NeoPaths(root), now=_FIXTURE_NOW, detail_level="trusted"), max_chars=80).text) <= 80


def test_projection_only_reads_active_day(tmp_path: Path):
    root = _projection_root(tmp_path)
    day_path = root / "data/days/2026/2026-07-10.json"
    day_path.write_text(json.dumps({"date":"2026-07-10","wake_at":"2026-07-10T08:00:00+09:00","sleep_at":None,"meals":[{"what":"병원 식사"}],"outings":[{"place":"secret address","returned_at":None}],"work_sessions":[{"checked_in_at":"2026-07-10T10:00:00+09:00","checked_out_at":None,"project_title_snapshot":"client secret"}],"todolist":[{"title":"계약서 보내기","done":False},{"title":"clean room","done":True}]}), encoding="utf-8")
    status = build_group_public_status(NeoPaths(root))
    assert status.meal_public_items == () and status.outing_public_places == () and status.has_ongoing_outing
    assert status.public_todo_items == () and status.public_completed_items == ("clean room",)
    assert status.public_work_summary is None


def _projection_root(root: Path) -> Path:
    (root / "config").mkdir(); (root / "schemas").mkdir(); (root / "data/indexes").mkdir(parents=True)
    (root / "config/app.json").write_text("{}", encoding="utf-8")
    (root / "schemas/project.schema.json").write_text("{}", encoding="utf-8")
    day_path = root / "data/days/2026/2026-07-10.json"; day_path.parent.mkdir(parents=True)
    day_path.write_text(json.dumps({"date":"2026-07-10","wake_at":None,"sleep_at":None,"meals":[],"outings":[],"work_sessions":[],"todolist":[]}), encoding="utf-8")
    (root / "data/indexes/current.json").write_text(json.dumps({"current_day":{"path":"data/days/2026/2026-07-10.json"}}), encoding="utf-8")
    return root
