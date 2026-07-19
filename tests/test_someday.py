from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from neo.domain import days as day_domain
from neo.domain import pending as pending_domain
from neo.domain import someday as someday_domain
from neo.errors import ValidationError
from neo.paths import NeoPaths
from neo.transaction import read_json
from neo.validation import schema_issues, validate_document
from neo.workspace import commit_workspace

from helpers import TempRepository, run_cli


def _valid_someday(title: str = "후보") -> dict:
    return someday_domain.add_someday_item(
        someday_domain.create_someday(), title, "설명"
    )


def test_action_item_variants_share_external_common_schema() -> None:
    repo = TempRepository(Path.cwd())
    try:
        day = day_domain.create_day("2026-07-11T08:00:00+09:00")
        day = day_domain.add_todo(day, "오늘 할 일")
        pending = pending_domain.add_pending_item(
            pending_domain.create_pending(), "잊지 않을 일"
        )
        someday = _valid_someday()
        for document, schema in [
            (day, "day.schema.json"),
            (pending, "pending.schema.json"),
            (someday, "someday.schema.json"),
        ]:
            assert schema_issues(repo.paths, document, schema, schema) == []

        item = dict(someday["items"][0])
        item.pop("title")
        invalid = {**someday, "items": [item]}
        assert schema_issues(repo.paths, invalid, "someday.schema.json", "someday")

        item = dict(someday["items"][0])
        item["someday_id"] = "not-a-uuid"
        assert schema_issues(
            repo.paths, {**someday, "items": [item]}, "someday.schema.json", "someday"
        )

        item = dict(someday["items"][0])
        item["unknown"] = True
        assert schema_issues(
            repo.paths, {**someday, "items": [item]}, "someday.schema.json", "someday"
        )
        validate_document(repo.paths, pending, "pending.schema.json", "pending")
        validate_document(repo.paths, day, "day.schema.json", "day")
    finally:
        repo.close()


def test_action_item_domain_is_immutable_and_preserves_variant_errors() -> None:
    pending = pending_domain.create_pending()
    original = json.loads(json.dumps(pending))
    pending = pending_domain.add_pending_item(pending, "  해야 할 일  ", "  설명  ")
    assert original == {"schema_version": 1, "items": [], "updated_at": original["updated_at"]}
    item = pending["items"][0]
    assert item["title"] == "해야 할 일" and item["description"] == "설명"
    timestamp = pending["updated_at"]
    same = pending_domain.set_pending_done(pending, item["pending_id"], False)
    assert same == pending and same["updated_at"] == timestamp
    done = pending_domain.set_pending_done(pending, item["pending_id"], True)
    undone = pending_domain.set_pending_done(done, item["pending_id"], False)
    removed = pending_domain.remove_pending_item(undone, item["pending_id"])
    assert removed["items"] == []
    with pytest.raises(ValidationError, match="Pending item not found"):
        pending_domain.set_pending_done(pending, str(uuid.uuid4()), True)
    with pytest.raises(ValidationError, match="Pending item not found"):
        pending_domain.remove_pending_item(pending, str(uuid.uuid4()))

    with pytest.raises(ValidationError, match="Todo item not found"):
        day_domain.remove_todo(day_domain.create_day("2026-07-11T08:00:00+09:00"), str(uuid.uuid4()))
    with pytest.raises(ValidationError, match="Someday item not found"):
        someday_domain.remove_someday_item(someday_domain.create_someday(), str(uuid.uuid4()))
    with pytest.raises(ValidationError, match="Item title must not be empty"):
        someday_domain.add_someday_item(someday_domain.create_someday(), "  ")


def test_someday_cli_lifecycle_and_existing_cli_regressions() -> None:
    repo = TempRepository(Path.cwd())
    try:
        listed = run_cli(repo.root, "--json", "someday", "list")
        assert listed.returncode == 0 and json.loads(listed.stdout)["count"] == 0
        assert not repo.paths.someday_file.exists()
        added = run_cli(
            repo.root, "--json", "someday", "add", "--title", "카페 가보기"
        )
        assert added.returncode == 0
        item = read_json(repo.paths.someday_file)["items"][0]
        sid = item["someday_id"]
        assert json.loads(run_cli(repo.root, "--json", "someday", "list").stdout)["count"] == 1
        assert run_cli(repo.root, "--json", "someday", "done", sid).returncode == 0
        assert json.loads(run_cli(repo.root, "--json", "someday", "list").stdout)["count"] == 0
        assert json.loads(run_cli(repo.root, "--json", "someday", "list", "--all").stdout)["count"] == 1
        assert run_cli(repo.root, "--json", "someday", "undo", sid).returncode == 0
        assert run_cli(repo.root, "--json", "someday", "remove", sid).returncode == 0

        assert run_cli(repo.root, "--json", "pending", "add", "--title", "pending 회귀").returncode == 0
        day = run_cli(repo.root, "--json", "day", "wake", "--at", "2026-07-11T08:00:00+09:00")
        assert day.returncode == 0
        todo = run_cli(repo.root, "--json", "day", "todo", "add", "--title", "todo 회귀")
        assert todo.returncode == 0
    finally:
        repo.close()


def test_workspace_collision_atomicity_and_derived_boundaries(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = TempRepository(Path.cwd())
    try:
        day_path = repo.paths.days / "2026" / "2026-07-11.json"
        day = day_domain.add_todo(day_domain.create_day("2026-07-11T08:00:00+09:00"), "기존 todo")
        commit_workspace(repo.paths, day_updates={day_path: day})
        before = {path: path.read_bytes() for path in [day_path, repo.paths.brief, repo.paths.current_index, repo.paths.project_index] if path.exists()}
        collision = _valid_someday()
        collision["items"][0]["someday_id"] = day["todolist"][0]["todo_id"]
        with pytest.raises(ValidationError, match="Duplicate UUID"):
            commit_workspace(repo.paths, someday_update=collision)
        after = {path: path.read_bytes() for path in before}
        assert after == before and not repo.paths.someday_file.exists()

        clean = _valid_someday()
        brief_before = repo.paths.brief.read_bytes()
        commit_workspace(repo.paths, someday_update=clean)
        assert repo.paths.brief.read_bytes() == brief_before
        assert repo.paths.current_index.read_bytes() == before[repo.paths.current_index]

        mixed_day = day_domain.add_todo(day, "혼합 todo")
        mixed_path = day_path
        mixed_someday = someday_domain.add_someday_item(clean, "혼합 변경")
        commit_workspace(repo.paths, day_updates={mixed_path: mixed_day}, someday_update=mixed_someday)
        assert "혼합 todo" in repo.paths.brief.read_text(encoding="utf-8")

        calls: list[object] = []
        monkeypatch.setattr("neo.workspace._git_commit", lambda *args: calls.append(args))
        same = someday_domain.set_someday_done(mixed_someday, mixed_someday["items"][0]["someday_id"], False)
        commit_workspace(repo.paths, someday_update=same)
        assert calls == []
    finally:
        repo.close()


def test_someday_agent_contract_is_explicit_and_low_activity() -> None:
    text = (Path(__file__).parents[1] / "protocols" / "someday.md").read_text(encoding="utf-8")
    assert "정확히 한 번" in text
    assert "저장하지 않는다" in text
    assert "양쪽에 동시에 저장하지 않는다" in text
    assert "자동 노출하지 않는다" in text
