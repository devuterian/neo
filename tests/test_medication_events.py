from __future__ import annotations

import json
from pathlib import Path

from helpers import TempRepository, run_cli
from neo.domain.lifestyle import (
    add_medication_event,
    medication_status,
    remove_medication_event,
    EXPECTED_MEDICATION_NAMES,
)
from neo.errors import ValidationError
from neo.utils import new_uuid


class TestMedicationEventDomain:
    """Domain-level medication event tests (no repository)."""


    def _empty_day(self):
        return {
            "schema_version": 2,
            "day_id": new_uuid(),
            "medications": [],
            "meals": [],
            "outings": [],
            "work_sessions": [],
            "created_at": "2026-07-12T10:00:00+09:00",
            "updated_at": "2026-07-12T10:00:00+09:00",
        }

    def test_take_creates_event(self):
        day = {"schema_version": 2, "day_id": "test", "medications": [], "meals": [], "outings": [], "work_sessions": [], "created_at": "2026-07-12T10:00:00+09:00", "updated_at": "2026-07-12T10:00:00+09:00"}
        day, med_id = add_medication_event(day, name="약 B", action="taken",
                                           occurred_at="2026-07-12T10:30:00+09:00")
        assert len(day["medications"]) == 1
        m = day["medications"][0]
        assert m["name"] == "약 B"
        assert m["action"] == "taken"
        assert m["medication_id"] == med_id
        assert m["occurred_at"] == "2026-07-12T10:30:00+09:00"

    def test_same_name_take_twice_succeeds(self):
        day = {"schema_version": 2, "day_id": "test", "medications": [], "meals": [], "outings": [], "work_sessions": [], "created_at": "2026-07-12T10:00:00+09:00", "updated_at": "2026-07-12T10:00:00+09:00"}
        day, id1 = add_medication_event(day, name="약 B", action="taken",
                                        occurred_at="2026-07-12T10:00:00+09:00")
        day, id2 = add_medication_event(day, name="약 B", action="taken",
                                        occurred_at="2026-07-12T22:00:00+09:00")
        assert len(day["medications"]) == 2
        assert id1 != id2
        assert day["medications"][0]["occurred_at"] == "2026-07-12T10:00:00+09:00"
        assert day["medications"][1]["occurred_at"] == "2026-07-12T22:00:00+09:00"

    def test_dose_and_note_preserved(self):
        day = {"schema_version": 2, "day_id": "test", "medications": [], "meals": [], "outings": [], "work_sessions": [], "created_at": "2026-07-12T10:00:00+09:00", "updated_at": "2026-07-12T10:00:00+09:00"}
        day, _ = add_medication_event(day, name="약 B", action="taken",
                                      dose="1정", note="식후")
        m = day["medications"][0]
        assert m["dose"] == "1정"
        assert m["note"] == "식후"

    def test_empty_name_rejected(self):
        day = {"schema_version": 2, "day_id": "test", "medications": [], "meals": [], "outings": [], "work_sessions": [], "created_at": "2026-07-12T10:00:00+09:00", "updated_at": "2026-07-12T10:00:00+09:00"}
        try:
            add_medication_event(day, name="  ", action="taken")
            assert False, "expected ValidationError"
        except ValidationError:
            pass

    def test_skip_creates_separate_event(self):
        day = {"schema_version": 2, "day_id": "test", "medications": [], "meals": [], "outings": [], "work_sessions": [], "created_at": "2026-07-12T10:00:00+09:00", "updated_at": "2026-07-12T10:00:00+09:00"}
        day, id1 = add_medication_event(day, name="약 B", action="taken",
                                        occurred_at="2026-07-12T10:00:00+09:00")
        day, id2 = add_medication_event(day, name="약 A", action="skipped",
                                        note="잊음")
        assert len(day["medications"]) == 2
        # Existing taken event unchanged
        assert day["medications"][0]["action"] == "taken"
        assert day["medications"][0]["medication_id"] == id1
        # New skip event
        assert day["medications"][1]["action"] == "skipped"
        assert day["medications"][1]["medication_id"] == id2
        assert day["medications"][1]["note"] == "잊음"

    def test_remove_by_medication_id(self):
        day = {"schema_version": 2, "day_id": "test", "medications": [], "meals": [], "outings": [], "work_sessions": [], "created_at": "2026-07-12T10:00:00+09:00", "updated_at": "2026-07-12T10:00:00+09:00"}
        day, id1 = add_medication_event(day, name="약 B", action="taken")
        day, id2 = add_medication_event(day, name="약 B", action="taken")
        day = remove_medication_event(day, id1)
        assert len(day["medications"]) == 1
        assert day["medications"][0]["medication_id"] == id2

    def test_remove_unknown_id_fails(self):
        day = {"schema_version": 2, "day_id": "test", "medications": [], "meals": [], "outings": [], "work_sessions": [], "created_at": "2026-07-12T10:00:00+09:00", "updated_at": "2026-07-12T10:00:00+09:00"}
        try:
            remove_medication_event(day, "nonexistent-id")
            assert False, "expected ValidationError"
        except ValidationError:
            pass

    def test_status_taken_counts(self):
        day = {"schema_version": 2, "day_id": "test", "medications": [], "meals": [], "outings": [], "work_sessions": [], "created_at": "2026-07-12T10:00:00+09:00", "updated_at": "2026-07-12T10:00:00+09:00"}
        day, _ = add_medication_event(day, name="약 B", action="taken",
                                      occurred_at="2026-07-12T10:00:00+09:00")
        day, _ = add_medication_event(day, name="약 B", action="taken",
                                      occurred_at="2026-07-12T22:00:00+09:00")
        day, _ = add_medication_event(day, name="약 A", action="skipped",
                                      note="잊음")
        status = medication_status(day)
        assert status["taken_counts"]["약 B"] == 2
        assert status["skipped"] == ["약 A"]
        assert status["missing"] == []  # 약 A is skipped, 약 B is taken
        assert status["total_records"] == 3

    def test_status_has_no_public_default_regimen(self):
        day = {"schema_version": 2, "day_id": "test", "medications": [], "meals": [], "outings": [], "work_sessions": [], "created_at": "2026-07-12T10:00:00+09:00", "updated_at": "2026-07-12T10:00:00+09:00"}
        # Recording one medicine does not invent another expected medicine.
        day, _ = add_medication_event(day, name="약 B", action="taken")
        status = medication_status(day)
        assert status["missing"] == []
        assert status["taken_counts"] == {"약 B": 1}

    def test_status_skipped_not_missing(self):
        day = {"schema_version": 2, "day_id": "test", "medications": [], "meals": [], "outings": [], "work_sessions": [], "created_at": "2026-07-12T10:00:00+09:00", "updated_at": "2026-07-12T10:00:00+09:00"}
        day, _ = add_medication_event(day, name="약 A", action="skipped", note="안 함")
        status = medication_status(day)
        assert "약 A" not in status["missing"]
        assert status["skipped"] == ["약 A"]


class TestMedicationEventCli:
    """CLI-level medication event tests."""

    def test_take_repeated_succeeds(self):
        repo = TempRepository(Path(__file__).resolve().parents[1])
        try:
            r = run_cli(repo.root, "--json", "day", "wake", "--at",
                        "2026-07-12T09:00:00+09:00")
            assert r.returncode == 0, r.stderr

            r = run_cli(repo.root, "--json", "day", "med", "take", "--name", "약 B",
                        "--at", "2026-07-12T10:00:00+09:00")
            assert r.returncode == 0, r.stderr
            data1 = json.loads(r.stdout)
            assert "medication_id" in data1

            r = run_cli(repo.root, "--json", "day", "med", "take", "--name", "약 B",
                        "--at", "2026-07-12T22:00:00+09:00")
            assert r.returncode == 0, r.stderr
            data2 = json.loads(r.stdout)
            assert data2["medication_id"] != data1["medication_id"]

            day_data = json.loads(
                (repo.paths.days / "2026" / "2026-07-12.json").read_text())
            assert len(day_data["medications"]) == 2
        finally:
            repo.close()

    def test_take_with_dose_and_note(self):
        repo = TempRepository(Path(__file__).resolve().parents[1])
        try:
            r = run_cli(repo.root, "--json", "day", "wake", "--at",
                        "2026-07-12T09:00:00+09:00")
            assert r.returncode == 0

            r = run_cli(repo.root, "--json", "day", "med", "take", "--name", "약 B",
                        "--dose", "1정", "--note", "식후")
            assert r.returncode == 0, r.stderr

            day_data = json.loads(
                (repo.paths.days / "2026" / "2026-07-12.json").read_text())
            m = day_data["medications"][0]
            assert m["dose"] == "1정"
            assert m["note"] == "식후"
        finally:
            repo.close()

    def test_skip_with_reason(self):
        repo = TempRepository(Path(__file__).resolve().parents[1])
        try:
            r = run_cli(repo.root, "--json", "day", "wake", "--at",
                        "2026-07-12T09:00:00+09:00")
            assert r.returncode == 0

            r = run_cli(repo.root, "--json", "day", "med", "skip", "--name", "약 A",
                        "--reason", "잊음")
            assert r.returncode == 0, r.stderr

            day_data = json.loads(
                (repo.paths.days / "2026" / "2026-07-12.json").read_text())
            assert len(day_data["medications"]) == 1
            assert day_data["medications"][0]["action"] == "skipped"
            assert day_data["medications"][0]["note"] == "잊음"
        finally:
            repo.close()

    def test_remove_by_id(self):
        repo = TempRepository(Path(__file__).resolve().parents[1])
        try:
            r = run_cli(repo.root, "--json", "day", "wake", "--at",
                        "2026-07-12T09:00:00+09:00")
            assert r.returncode == 0

            r = run_cli(repo.root, "--json", "day", "med", "take", "--name", "약 B")
            assert r.returncode == 0
            med_id = json.loads(r.stdout)["medication_id"]

            r = run_cli(repo.root, "--json", "day", "med", "remove", med_id)
            assert r.returncode == 0, r.stderr

            day_data = json.loads(
                (repo.paths.days / "2026" / "2026-07-12.json").read_text())
            assert len(day_data["medications"]) == 0
        finally:
            repo.close()

    def test_remove_unknown_id_fails(self):
        repo = TempRepository(Path(__file__).resolve().parents[1])
        try:
            r = run_cli(repo.root, "--json", "day", "wake", "--at",
                        "2026-07-12T09:00:00+09:00")
            assert r.returncode == 0

            r = run_cli(repo.root, "--json", "day", "med", "remove",
                        "00000000-0000-0000-0000-000000000000")
            assert r.returncode != 0
        finally:
            repo.close()

    def test_status_includes_summary(self):
        repo = TempRepository(Path(__file__).resolve().parents[1])
        try:
            r = run_cli(repo.root, "--json", "day", "wake", "--at",
                        "2026-07-12T09:00:00+09:00")
            assert r.returncode == 0

            run_cli(repo.root, "--json", "day", "med", "take", "--name", "약 B")

            r = run_cli(repo.root, "--json", "day", "med", "status")
            assert r.returncode == 0
            data = json.loads(r.stdout)
            assert "summary" in data
            assert "expected" in data["summary"]
            assert "missing" in data["summary"]
            assert "taken_counts" in data["summary"]
            assert "skipped" in data["summary"]
            assert data["summary"]["missing"] == []
            assert data["summary"]["taken_counts"]["약 B"] == 1
        finally:
            repo.close()

    def test_new_day_has_empty_medications(self):
        repo = TempRepository(Path(__file__).resolve().parents[1])
        try:
            r = run_cli(repo.root, "--json", "day", "wake", "--at",
                        "2026-07-12T09:00:00+09:00")
            assert r.returncode == 0

            day_data = json.loads(
                (repo.paths.days / "2026" / "2026-07-12.json").read_text())
            assert day_data["medications"] == []
            assert day_data["schema_version"] == 2
        finally:
            repo.close()

    def test_past_date_target(self):
        repo = TempRepository(Path(__file__).resolve().parents[1])
        try:
            r = run_cli(repo.root, "--json", "day", "wake", "--at",
                        "2026-07-11T09:00:00+09:00")
            assert r.returncode == 0

            r = run_cli(repo.root, "--json", "day", "--date", "2026-07-11",
                        "med", "take", "--name", "약 B",
                        "--at", "2026-07-11T22:00:00+09:00")
            assert r.returncode == 0, r.stderr

            day_data = json.loads(
                (repo.paths.days / "2026" / "2026-07-11.json").read_text())
            assert len(day_data["medications"]) == 1
            assert day_data["medications"][0]["name"] == "약 B"
        finally:
            repo.close()

    def test_invalid_action_rejected(self):
        from neo.domain.lifestyle import add_medication_event
        from neo.errors import ValidationError
        day = {"schema_version": 2, "day_id": "test", "medications": [], "meals": [], "outings": [], "work_sessions": [], "created_at": "2026-07-12T10:00:00+09:00", "updated_at": "2026-07-12T10:00:00+09:00"}
        try:
            add_medication_event(day, name="약 B", action="did_not_take")
            assert False
        except ValidationError:
            pass
