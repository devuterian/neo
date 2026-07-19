from __future__ import annotations

import json
from pathlib import Path

import pytest

from helpers import TempRepository, run_cli
from neo.domain.days import add_note, create_day
from neo.mutations import MutationService, schema_coverage
from neo.transaction import read_json
from neo.workspace import commit_workspace


class TestMutationService:
    def setup_method(self) -> None:
        self.repo = TempRepository(Path(__file__).resolve().parents[1])
        self.service = MutationService(self.repo.paths)

    def teardown_method(self) -> None:
        self.repo.close()

    def _seed_day(self) -> dict:
        day = create_day("2026-07-11T09:13:59+09:00")
        day = add_note(day, "fixture note")
        path = self.repo.paths.days / "2026" / "2026-07-11.json"
        commit_workspace(self.repo.paths, day_updates={path: day})
        return day

    def test_schema_coverage_and_capability_matrix(self) -> None:
        coverage = schema_coverage(self.repo.paths.schemas)
        assert set(coverage) == {
            path.name for path in self.repo.paths.schemas.glob("*.schema.json")
        }
        capabilities = self.service.capabilities()
        single = self.service.capabilities("day")
        assert [item["resource"] for item in single["resources"]] == ["day"]
        authoritative = {
            item["resource"] for item in capabilities["resources"]
            if item["kind"] == "authoritative"
        }
        assert authoritative == {"app", "day", "project", "pending", "someday", "fridge", "medical"}
        assert self.service.capabilities(owner_group=True)["resources"][-1]["actions"] == []

    def test_day_correct_changes_only_wake_and_preserves_note(self) -> None:
        original = self._seed_day()
        path = self.repo.paths.days / "2026" / "2026-07-11.json"
        before_bytes = path.read_bytes()
        result = self.service.mutate(
            "correct",
            "day",
            "2026-07-11",
            field="wake_at",
            value="2026-07-11T07:46:00+09:00",
            reason="fixture correction",
        )
        updated = read_json(path)
        assert result["success"] is True
        assert result["before"] == {"wake_at": original["wake_at"]}
        assert result["after"] == {"wake_at": updated["wake_at"]}
        assert updated["wake_at"] == "2026-07-11T07:46:00+09:00"
        assert updated["notes"] == original["notes"]
        assert path.read_bytes() != before_bytes

    def test_day_correct_rejects_invalid_order_without_writing(self) -> None:
        self._seed_day()
        path = self.repo.paths.days / "2026" / "2026-07-11.json"
        before = path.read_bytes()
        with pytest.raises(Exception, match="wake_at date must match"):
            self.service.mutate(
                "correct",
                "day",
                "2026-07-11",
                field="wake_at",
                value="2026-07-12T07:46:00+09:00",
                reason="bad fixture correction",
            )
        assert path.read_bytes() == before

    def test_revision_conflict_and_delete_confirmation(self) -> None:
        self._seed_day()
        current = read_json(self.repo.paths.days / "2026" / "2026-07-11.json")
        with pytest.raises(Exception, match="revision conflict"):
            self.service.mutate(
                "update", "day", "2026-07-11",
                field="wake_at", value=current["wake_at"],
                expected_revision="stale",
            )
        with pytest.raises(Exception, match="requires --confirm"):
            self.service.mutate("delete", "day", "2026-07-11", reason="fixture")
        assert (self.repo.paths.days / "2026" / "2026-07-11.json").is_file()

    def test_app_is_typed_and_singleton_delete_resets_without_removing_file(self) -> None:
        result = self.service.mutate(
            "correct", "app", field="auto_wake", value="never", reason="fixture correction"
        )
        assert result["success"] is True
        assert read_json(self.repo.paths.config)["auto_wake"] == "never"
        deleted = self.service.mutate("delete", "app", reason="fixture reset", confirm=True)
        assert deleted["success"] is True
        assert self.repo.paths.config.is_file()
        assert read_json(self.repo.paths.config)["auto_wake"] == "ask"

    def test_pending_someday_and_private_boundaries(self) -> None:
        pending = self.service.mutate("add", "pending", typed={"title": "fixture pending"})
        someday = self.service.mutate("add", "someday", typed={"title": "fixture someday"})
        assert pending["success"] and someday["success"]
        assert self.service.list("pending")["count"] == 1
        assert self.service.list("someday")["count"] == 1
        with pytest.raises(Exception, match="Private resource"):
            self.service.get("private-spark")
        with pytest.raises(Exception, match="does not support"):
            self.service.mutate("delete", "project-index", "anything", reason="fixture", confirm=True)

    def test_cli_capabilities_json(self) -> None:
        result = run_cli(self.repo.root, "--json", "resource", "capabilities")
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["success"] is True
        assert payload["schema_classifications"]["action-item.schema.json"] == "embedded"


class TestContainerDelete:
    def setup_method(self) -> None:
        self.repo = TempRepository(Path(__file__).resolve().parents[1])
        self.service = MutationService(self.repo.paths)

    def teardown_method(self) -> None:
        self.repo.close()

    def test_pending_add_delete_roundtrip(self) -> None:
        added = self.service.mutate("add", "pending", typed={"title": "fixture item"})
        item_id = added["target"]
        assert self.service.list("pending")["count"] == 1
        deleted = self.service.mutate(
            "delete", "pending", item_id, reason="cleanup", confirm=True,
        )
        assert deleted["success"] is True
        assert deleted["before"] is not None
        assert deleted["after"] is None or deleted.get("target") == item_id
        remaining = self.service.list("pending")
        assert remaining["count"] == 0

    def test_someday_add_delete_roundtrip(self) -> None:
        added = self.service.mutate("add", "someday", typed={"title": "fixture someday"})
        item_id = added["target"]
        assert self.service.list("someday")["count"] == 1
        deleted = self.service.mutate(
            "delete", "someday", item_id, reason="cleanup", confirm=True,
        )
        assert deleted["success"] is True
        remaining = self.service.list("someday")
        assert remaining["count"] == 0

    def test_fridge_add_delete_roundtrip(self) -> None:
        added = self.service.mutate("add", "fridge", typed={"name": "fixture food", "quantity": 1})
        item_id = added["target"]
        assert self.service.list("fridge")["count"] == 1
        deleted = self.service.mutate(
            "delete", "fridge", item_id, reason="consumed", confirm=True,
        )
        assert deleted["success"] is True
        remaining = self.service.list("fridge")
        assert remaining["count"] == 0

    def test_container_delete_preserves_other_items(self) -> None:
        first = self.service.mutate("add", "pending", typed={"title": "first"})
        second = self.service.mutate("add", "pending", typed={"title": "second"})
        self.service.mutate(
            "delete", "pending", first["target"], reason="done", confirm=True,
        )
        remaining = self.service.list("pending")
        assert remaining["count"] == 1
        assert remaining["items"][0]["title"] == "second"

    def test_container_delete_rollback_on_validation_failure(self) -> None:
        added = self.service.mutate("add", "pending", typed={"title": "fixture"})
        path = self.repo.paths.pending_file
        before = path.read_bytes()
        with pytest.raises(Exception, match="not found"):
            self.service.mutate(
                "delete", "pending", "nonexistent-id", reason="bad", confirm=True,
            )
        assert path.read_bytes() == before


class TestCapabilityMatrix:
    def setup_method(self) -> None:
        self.repo = TempRepository(Path(__file__).resolve().parents[1])
        self.service = MutationService(self.repo.paths)

    def teardown_method(self) -> None:
        self.repo.close()

    def test_app_has_no_add_action(self) -> None:
        caps = self.service.capabilities("app")
        app_caps = caps["resources"][0]
        assert app_caps["resource"] == "app"
        assert "add" not in app_caps["actions"]
        assert "update" in app_caps["actions"]
        assert "correct" in app_caps["actions"]
        assert "delete" in app_caps["actions"]

    def test_day_has_all_actions(self) -> None:
        caps = self.service.capabilities("day")
        day_caps = caps["resources"][0]
        assert set(day_caps["actions"]) == {"add", "update", "correct", "delete"}

    def test_pending_someday_fridge_have_all_actions(self) -> None:
        for resource in ("pending", "someday", "fridge"):
            caps = self.service.capabilities(resource)
            r_caps = caps["resources"][0]
            assert set(r_caps["actions"]) == {"add", "update", "correct", "delete"}, f"{resource} actions mismatch"

    def test_medical_uses_dedicated_safe_commands(self) -> None:
        caps = self.service.capabilities("medical")
        medical_caps = caps["resources"][0]
        assert medical_caps["actions"] == []

    def test_derived_resources_have_no_actions(self) -> None:
        for resource in ("calendar-index", "current-index", "project-index"):
            caps = self.service.capabilities(resource)
            r_caps = caps["resources"][0]
            assert r_caps["actions"] == [], f"{resource} should have no actions"

    def test_private_resource_has_no_actions(self) -> None:
        caps = self.service.capabilities("private-spark")
        r_caps = caps["resources"][0]
        assert r_caps["actions"] == []


class TestCorrectionAudit:
    def setup_method(self) -> None:
        self.repo = TempRepository(Path(__file__).resolve().parents[1])
        self.service = MutationService(self.repo.paths)

    def teardown_method(self) -> None:
        self.repo.close()

    def _seed_day(self) -> dict:
        day = create_day("2026-07-11T09:13:59+09:00")
        day = add_note(day, "fixture note")
        path = self.repo.paths.days / "2026" / "2026-07-11.json"
        commit_workspace(self.repo.paths, day_updates={path: day})
        return day

    def test_correct_creates_audit_record(self) -> None:
        from neo.audit import record_correction
        self._seed_day()
        self.service.mutate(
            "correct", "day", "2026-07-11",
            field="wake_at", value="2026-07-11T07:46:00+09:00",
            reason="실제 기상시각 정정",
        )
        audit_dir = self.repo.paths.audit_dir
        assert audit_dir.is_dir()
        files = list(audit_dir.glob("*.jsonl"))
        assert len(files) == 1
        import json
        with files[0].open() as f:
            record = json.loads(f.readline())
        assert record["action"] == "correct"
        assert record["resource"] == "day"
        assert record["target"] == "2026-07-11"
        assert record["reason"] == "실제 기상시각 정정"
        assert "wake_at" in record["changed_fields"]
        assert record["before"] is not None
        assert record["after"] is not None

    def test_update_does_not_create_audit(self) -> None:
        self._seed_day()
        self.service.mutate(
            "update", "day", "2026-07-11",
            field="wake_at", value="2026-07-11T08:00:00+09:00",
        )
        audit_dir = self.repo.paths.audit_dir
        if audit_dir.is_dir():
            files = list(audit_dir.glob("*.jsonl"))
            assert len(files) == 0

    def test_rollback_does_not_create_audit(self) -> None:
        self._seed_day()
        with pytest.raises(Exception, match="wake_at date must match"):
            self.service.mutate(
                "correct", "day", "2026-07-11",
                field="wake_at", value="2026-07-12T07:46:00+09:00",
                reason="bad correction",
            )
        audit_dir = self.repo.paths.audit_dir
        if audit_dir.is_dir():
            files = list(audit_dir.glob("*.jsonl"))
            assert len(files) == 0


class TestFullCRUD:
    def setup_method(self) -> None:
        self.repo = TempRepository(Path(__file__).resolve().parents[1])
        self.service = MutationService(self.repo.paths)

    def teardown_method(self) -> None:
        self.repo.close()

    def _seed_day(self) -> dict:
        day = create_day("2026-07-11T09:13:59+09:00")
        day = add_note(day, "fixture note")
        path = self.repo.paths.days / "2026" / "2026-07-11.json"
        commit_workspace(self.repo.paths, day_updates={path: day})
        return day

    def test_day_full_crud(self) -> None:
        # Add
        result = self.service.mutate("add", "day", typed={"wake_at": "2026-07-12T08:00:00+09:00"})
        assert result["success"] is True
        assert result["action"] == "add"
        # Get
        got = self.service.get("day", "2026-07-12")
        assert got["date"] == "2026-07-12"
        # List
        lst = self.service.list("day")
        assert lst["count"] >= 1
        # Update
        updated = self.service.mutate("update", "day", "2026-07-12", field="status", value="closed")
        assert updated["success"] is True
        assert updated["action"] == "update"
        # Correct
        corrected = self.service.mutate(
            "correct", "day", "2026-07-12",
            field="wake_at", value="2026-07-12T07:00:00+09:00",
            reason="test correction",
        )
        assert corrected["success"] is True
        assert corrected["action"] == "correct"
        assert corrected["reason"] == "test correction"
        # Delete
        deleted = self.service.mutate("delete", "day", "2026-07-12", reason="test cleanup", confirm=True)
        assert deleted["success"] is True
        assert deleted["action"] == "delete"

    def test_project_full_crud(self) -> None:
        # Add
        result = self.service.mutate("add", "project", typed={"title": "Test Project", "description": "A test"})
        assert result["success"] is True
        slug = result["target"]
        # Get
        got = self.service.get("project", slug)
        assert got["title"] == "Test Project"
        # List
        lst = self.service.list("project")
        assert lst["count"] >= 1
        # Update
        updated = self.service.mutate("update", "project", slug, field="title", value="Updated Project")
        assert updated["success"] is True
        # Correct
        corrected = self.service.mutate(
            "correct", "project", slug,
            field="description", value="corrected desc",
            reason="test correction",
        )
        assert corrected["success"] is True
        # Delete
        deleted = self.service.mutate("delete", "project", slug, reason="test cleanup", confirm=True)
        assert deleted["success"] is True

    def test_pending_full_crud(self) -> None:
        # Add
        added = self.service.mutate("add", "pending", typed={"title": "Test Pending"})
        assert added["success"] is True
        item_id = added["target"]
        # Get
        got = self.service.get("pending", item_id)
        assert got["title"] == "Test Pending"
        # List
        lst = self.service.list("pending")
        assert lst["count"] >= 1
        # Update
        updated = self.service.mutate("update", "pending", item_id, field="title", value="Updated Pending")
        assert updated["success"] is True
        # Correct
        corrected = self.service.mutate(
            "correct", "pending", item_id,
            field="title", value="Corrected Pending",
            reason="test correction",
        )
        assert corrected["success"] is True
        # Delete
        deleted = self.service.mutate("delete", "pending", item_id, reason="test cleanup", confirm=True)
        assert deleted["success"] is True

    def test_someday_full_crud(self) -> None:
        added = self.service.mutate("add", "someday", typed={"title": "Test Someday"})
        assert added["success"] is True
        item_id = added["target"]
        got = self.service.get("someday", item_id)
        assert got["title"] == "Test Someday"
        lst = self.service.list("someday")
        assert lst["count"] >= 1
        updated = self.service.mutate("update", "someday", item_id, field="title", value="Updated")
        assert updated["success"] is True
        corrected = self.service.mutate(
            "correct", "someday", item_id,
            field="title", value="Corrected",
            reason="test correction",
        )
        assert corrected["success"] is True
        deleted = self.service.mutate("delete", "someday", item_id, reason="test cleanup", confirm=True)
        assert deleted["success"] is True

    def test_fridge_full_crud(self) -> None:
        added = self.service.mutate("add", "fridge", typed={"name": "Test Food", "quantity": 1})
        assert added["success"] is True
        item_id = added["target"]
        got = self.service.get("fridge", item_id)
        assert got["name"] == "Test Food"
        lst = self.service.list("fridge")
        assert lst["count"] >= 1
        updated = self.service.mutate("update", "fridge", item_id, field="name", value="Updated Food")
        assert updated["success"] is True
        corrected = self.service.mutate(
            "correct", "fridge", item_id,
            field="name", value="Corrected Food",
            reason="test correction",
        )
        assert corrected["success"] is True
        deleted = self.service.mutate("delete", "fridge", item_id, reason="consumed", confirm=True)
        assert deleted["success"] is True

    def test_app_update_correct_delete_reset(self) -> None:
        # App cannot be added, only updated/corrected/deleted(reset)
        with pytest.raises(Exception, match="does not support"):
            self.service.mutate("add", "app", typed={})
        # Update
        updated = self.service.mutate("update", "app", field="auto_wake", value="never")
        assert updated["success"] is True
        # Correct
        corrected = self.service.mutate(
            "correct", "app", field="auto_wake", value="ask",
            reason="test correction",
        )
        assert corrected["success"] is True
        # Delete (reset)
        deleted = self.service.mutate("delete", "app", reason="test reset", confirm=True)
        assert deleted["success"] is True

    def test_immutable_field_rejection(self) -> None:
        self._seed_day()
        # "date" is not in _FIELD_MAP, so it's rejected as unsupported
        # (immutable fields that aren't in the field map are caught first)
        with pytest.raises(Exception, match="Unsupported|immutable"):
            self.service.mutate("update", "day", "2026-07-11", field="date", value="2026-07-12")

    def test_stale_revision_rejection(self) -> None:
        self._seed_day()
        with pytest.raises(Exception, match="revision conflict"):
            self.service.mutate(
                "update", "day", "2026-07-11",
                field="wake_at", value="2026-07-11T08:00:00+09:00",
                expected_revision="stale-revision",
            )

    def test_not_found_errors(self) -> None:
        with pytest.raises(Exception, match="[Nn]o.*found|not found"):
            self.service.get("day", "2099-01-01")
        with pytest.raises(Exception, match="[Nn]o.*found|not found"):
            self.service.mutate("update", "day", "2099-01-01", field="status", value="closed")

    def test_delete_requires_confirm_and_reason(self) -> None:
        self._seed_day()
        with pytest.raises(Exception, match="confirm"):
            self.service.mutate("delete", "day", "2026-07-11", reason="test")
        with pytest.raises(Exception, match="reason"):
            self.service.mutate("delete", "day", "2026-07-11", confirm=True)

    def test_correct_requires_reason(self) -> None:
        self._seed_day()
        with pytest.raises(Exception, match="reason"):
            self.service.mutate(
                "correct", "day", "2026-07-11",
                field="wake_at", value="2026-07-11T08:00:00+09:00",
            )

    def test_unsupported_action(self) -> None:
        with pytest.raises(Exception, match="Unsupported"):
            self.service.mutate("invalid", "day", "2026-07-11")
