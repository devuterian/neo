from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from neo.brief_projection import load_brief_projection
from neo.group_qa import (
    build_trusted_group_brief_context,
    build_trusted_group_brief_summary,
)
from neo.paths import NeoPaths
from neo.renderer import render_brief_projection


_NOW = datetime(2026, 7, 10, 12, 0, tzinfo=ZoneInfo("Asia/Seoul"))


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _root(root: Path) -> Path:
    (root / "config").mkdir()
    (root / "schemas").mkdir()
    (root / "config/app.json").write_text("{}", encoding="utf-8")
    (root / "schemas/project.schema.json").write_text("{}", encoding="utf-8")

    _write(
        root / "data/days/2026/2026-07-10.json",
        {
            "date": "2026-07-10",
            "status": "active",
            "wake_at": "2026-07-10T08:00:00+09:00",
            "sleep_at": None,
            "workday_capacity": 0.5,
            "mood": {
                "summary": "차분함",
                "reason": "공유 가능한 기분 이유",
            },
            "todolist": [
                {
                    "title": "오늘 공개 할 일",
                    "description": "할 일 설명",
                    "done": False,
                },
                {
                    "title": "완료한 일",
                    "description": "",
                    "done": True,
                },
            ],
            "meals": [
                {
                    "tag": "breakfast",
                    "what": "카레 + 쌀밥",
                    "occurred_at": "2026-07-10T08:30:00+09:00",
                }
            ],
            "outings": [
                {
                    "place": "샘플역",
                    "purpose": "친구 만나기",
                    "left_at": "2026-07-10T18:00:00+09:00",
                    "returned_at": None,
                }
            ],
            "work_sessions": [
                {
                    "task_title_snapshot": "공유 태스크",
                    "checked_in_at": "2026-07-10T10:00:00+09:00",
                    "checked_out_at": None,
                    "note": "raw work-session note must stay out",
                }
            ],
            "work_plan": [
                {
                    "project_id": "project-1",
                    "project_title_snapshot": "공유 프로젝트",
                    "milestone_title_snapshot": "공유 마일스톤",
                    "task_id": "task-1",
                    "task_title_snapshot": "공유 태스크",
                }
            ],
            "medications": [
                {
                    "name": "약 B",
                    "taken": False,
                    "taken_at": None,
                    "note": "브리프에 보이는 약 메모",
                }
            ],
            "external_schedule_snapshot": [
                {
                    "title": "친구 A 만나기",
                    "starts_at": "2026-07-10T18:00:00+09:00",
                    "ends_at": "2026-07-10T23:00:00+09:00",
                }
            ],
            "notes": [
                {
                    "text": "raw day note private spark must stay out",
                }
            ],
        },
    )
    _write(
        root / "data/projects/project.json",
        {
            "project_id": "project-1",
            "title": "공유 프로젝트",
            "status": "active",
            "waiting": None,
            "pause": None,
            "current_milestone_id": "milestone-1",
            "deadline_calendar_event_id": "deadline-event",
            "milestones": [
                {
                    "milestone_id": "milestone-1",
                    "title": "공유 마일스톤",
                    "remaining_effort": 2.5,
                    "calendar_event_id": "milestone-event",
                    "tasks": [
                        {
                            "task_id": "task-1",
                            "title": "공유 태스크",
                            "status": "todo",
                            "notes": [
                                {
                                    "text": "raw task note must stay out",
                                }
                            ],
                        }
                    ],
                }
            ],
            "decisions": [
                {
                    "title": "raw decision title must stay out",
                    "detail": "raw decision detail must stay out",
                }
            ],
        },
    )
    _write(
        root / "data/indexes/calendar.json",
        {
            "source": {
                "status": "available",
                "fetched_at": "2026-07-10T09:00:00+09:00",
                "error": None,
            },
            "events": {
                "milestone-event": {
                    "starts_at": "2026-07-15T12:00:00+09:00",
                },
                "deadline-event": {
                    "starts_at": "2026-07-20T12:00:00+09:00",
                },
            },
        },
    )
    _write(
        root / "data/medical.json",
        {
            "schema_version": 1,
            "records": [{
                "medical_id": "00000000-0000-4000-8000-000000000001",
                "provider": "샘플 병원",
                "title": "정기 검진",
                "last_date": "2026-07-01",
                "cycle_days": 21,
                "kind": "검진",
                "note": "비공개 병원 메모",
                "updated_at": "2026-07-01T00:00:00+09:00"
            }],
            "updated_at": "2026-07-01T00:00:00+09:00"
        },
    )
    _write(
        root / "data/pending.json",
        {
            "items": [
                {
                    "title": "밀린 공개 작업",
                    "description": "밀린 일 설명",
                    "done": False,
                }
            ]
        },
    )
    _write(
        root / "data/message-log/2026-07-10.jsonl",
        {"content": "raw message log must stay out"},
    )
    _write(
        root / "data/private/spark/2026-07.json",
        {"records": [{"note": "raw private spark record must stay out"}]},
    )
    return root


def test_markdown_and_trusted_context_share_brief_projection(tmp_path: Path) -> None:
    root = _root(tmp_path)
    paths = NeoPaths(root)
    projection = load_brief_projection(
        paths,
        generated_at=_NOW.isoformat(timespec="seconds"),
    )

    markdown = render_brief_projection(projection)
    context, summary = build_trusted_group_brief_context(paths, now=_NOW)

    assert summary is not None
    assert summary.current_life_day == "2026-07-10"
    assert summary.open_pending_count == 1
    assert summary.open_medication_count == 0
    assert summary.open_project_count == 1

    for visible_text in (
        "밀린 공개 작업",
        "밀린 일 설명",
        "차분함",
        "공유 가능한 기분 이유",
        "카레 + 쌀밥",
        "약 B",
        "브리프에 보이는 약 메모",
        "샘플역",
        "친구 만나기",
        "친구 A 만나기",
        "공유 프로젝트",
        "공유 마일스톤",
        "공유 태스크",
        "2026-07-15T12:00:00+09:00",
        "2026-07-20T12:00:00+09:00",
    ):
        assert visible_text in markdown
        assert visible_text in context

    assert "source=shared BriefProjection used by brief.md" in context
    assert "rendered_brief_file_read=false" in context
    assert "비공개 병원 메모" not in markdown
    assert "비공개 병원 메모" not in context
    assert not (root / "data/indexes/brief.json").exists()


def test_trusted_projection_ignores_rendered_brief_and_nonbrief_sources(tmp_path: Path) -> None:
    root = _root(tmp_path)
    (root / "brief.md").write_text(
        "# malicious brief\nbrief parser injection token exact address",
        encoding="utf-8",
    )

    paths = NeoPaths(root)
    projection = load_brief_projection(
        paths,
        generated_at=_NOW.isoformat(timespec="seconds"),
    )
    markdown = render_brief_projection(projection)
    context, summary = build_trusted_group_brief_context(paths, now=_NOW)

    assert summary is not None
    for excluded_text in (
        "brief parser injection",
        "exact address",
        "raw day note",
        "private spark must stay out",
        "raw work-session note",
        "raw task note",
        "raw decision title",
        "raw decision detail",
        "raw message log",
        "raw private spark record",
    ):
        assert excluded_text not in markdown
        assert excluded_text not in context


def test_summary_is_available_without_a_rendered_brief_file(tmp_path: Path) -> None:
    root = _root(tmp_path)
    assert not (root / "brief.md").exists()

    summary = build_trusted_group_brief_summary(NeoPaths(root), now=_NOW)

    assert summary is not None
    assert summary.current_life_day == "2026-07-10"
