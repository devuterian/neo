from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from helpers import TempRepository, run_cli


SOURCE = Path(__file__).resolve().parents[1]


def _json(result):
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_log_solo_with_ended_at_only():
    repo = TempRepository(SOURCE)
    try:
        _json(run_cli(repo.root, "--json", "day", "wake", "--at", "2026-07-04T16:02:30+09:00"))
        result = _json(
            run_cli(
                repo.root,
                "--json",
                "private",
                "spark",
                "log",
                "--kind",
                "solo",
                "--ended-at",
                "2026-07-05T03:40:00+09:00",
            )
        )
        assert result["ok"] is True
        assert result["path"] == "data/private/spark/2026/2026-07.json"
        store = json.loads((repo.root / result["path"]).read_text(encoding="utf-8"))
        assert store["records"][0]["life_day"] == "2026-07-04"
        assert store["records"][0]["kind"] == "solo"
        assert store["records"][0]["started_at"] is None
    finally:
        repo.close()


def test_log_together_with_partner_and_none_record():
    repo = TempRepository(SOURCE)
    try:
        together = _json(
            run_cli(
                repo.root,
                "--json",
                "private",
                "spark",
                "log",
                "--kind",
                "together",
                "--life-day",
                "2026-07-04",
                "--partner",
                "someone",
                "--ended-at",
                "2026-07-05T04:10:00+09:00",
            )
        )
        none = _json(
            run_cli(
                repo.root,
                "--json",
                "private",
                "spark",
                "log",
                "--kind",
                "none",
                "--life-day",
                "2026-07-04",
                "--allow-imprecise",
            )
        )
        assert together["ok"] is True
        assert none["ok"] is True
        listed = _json(run_cli(repo.root, "--json", "private", "spark", "list", "--month", "2026-07"))
        assert listed["count"] == 2
        assert {record["kind"] for record in listed["records"]} == {"together", "none"}
        assert "partner" not in listed["records"][0]
    finally:
        repo.close()


def test_edit_updates_only_selected_fields_and_remove_deletes_record():
    repo = TempRepository(SOURCE)
    try:
        logged = _json(
            run_cli(
                repo.root,
                "--json",
                "private",
                "spark",
                "log",
                "--kind",
                "solo",
                "--life-day",
                "2026-07-04",
                "--ended-at",
                "2026-07-05T03:40:00+09:00",
            )
        )
        record_id = logged["id"]
        before = _json(run_cli(repo.root, "--json", "private", "spark", "list", "--include-notes"))["records"][0]
        time.sleep(1)
        edited = _json(
            run_cli(
                repo.root,
                "--json",
                "private",
                "spark",
                "edit",
                record_id,
                "--mood",
                "calm",
            )
        )["record"]
        assert edited["mood"] == "calm"
        assert edited["kind"] == before["kind"]
        assert edited["updated_at"] != before["updated_at"]
        removed = _json(run_cli(repo.root, "--json", "private", "spark", "remove", record_id, "--approve"))
        assert removed["ok"] is True
        assert _json(run_cli(repo.root, "--json", "private", "spark", "list"))["count"] == 0
    finally:
        repo.close()


def test_list_filters_and_report_output_are_private_by_default(tmp_path):
    repo = TempRepository(SOURCE)
    try:
        _json(
            run_cli(
                repo.root,
                "--json",
                "private",
                "spark",
                "log",
                "--kind",
                "solo",
                "--life-day",
                "2026-07-04",
                "--ended-at",
                "2026-07-05T03:40:00+09:00",
                "--note",
                "private note",
            )
        )
        by_day = _json(run_cli(repo.root, "--json", "private", "spark", "list", "--life-day", "2026-07-04"))
        assert by_day["count"] == 1
        assert "note" not in by_day["records"][0]

        report_path = tmp_path / "spark-report.md"
        report = _json(
            run_cli(
                repo.root,
                "--json",
                "private",
                "spark",
                "report",
                "--month",
                "2026-07",
                "--output",
                str(report_path),
            )
        )
        assert report["committed"] is False
        text = report_path.read_text(encoding="utf-8")
        assert "total: 1" in text
        assert "private note" not in text
    finally:
        repo.close()


def test_doctor_and_brief_do_not_expose_private_details():
    repo = TempRepository(SOURCE)
    try:
        _json(
            run_cli(
                repo.root,
                "--json",
                "private",
                "spark",
                "log",
                "--kind",
                "together",
                "--life-day",
                "2026-07-04",
                "--partner",
                "hidden",
                "--ended-at",
                "2026-07-05T03:40:00+09:00",
                "--note",
                "secret detail",
            )
        )
        doctor = _json(run_cli(repo.root, "--json", "doctor"))
        rendered = json.dumps(doctor, ensure_ascii=False)
        assert doctor["private_spark"]["records_this_month"] >= 0
        assert "hidden" not in rendered
        assert "secret detail" not in rendered
        assert "secret detail" not in (repo.root / "brief.md").read_text(encoding="utf-8")
    finally:
        repo.close()


def test_validation_catches_duplicate_id_bad_kind_and_datetime_order():
    repo = TempRepository(SOURCE)
    try:
        path = repo.root / "data/private/spark/2026/2026-07.json"
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "records": [
                        {
                            "id": "spark_20260705_034000_abcd",
                            "life_day": "2026-07-04",
                            "kind": "solo",
                            "started_at": "2026-07-05T04:00:00+09:00",
                            "ended_at": "2026-07-05T03:00:00+09:00",
                            "created_at": "2026-07-05T03:40:00+09:00",
                            "updated_at": "2026-07-05T03:40:00+09:00",
                        },
                        {
                            "id": "spark_20260705_034000_abcd",
                            "life_day": "2026-07-04",
                            "kind": "bad",
                            "created_at": "2026-07-05T03:40:00+09:00",
                            "updated_at": "2026-07-05T03:40:00+09:00",
                        },
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        result = run_cli(repo.root, "--json", "validate")
        assert result.returncode == 2
        body = json.loads(result.stderr)
        text = json.dumps(body, ensure_ascii=False)
        assert "Duplicate private spark id" in text
        assert "is not one of" in text
        assert "ends before it starts" in text
    finally:
        repo.close()


def test_report_does_not_stage_or_commit_when_repo_has_git(tmp_path):
    repo = TempRepository(SOURCE)
    try:
        subprocess.run(["git", "init"], cwd=repo.root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo.root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo.root, check=True)
        subprocess.run(["git", "add", "."], cwd=repo.root, check=True)
        subprocess.run(["git", "commit", "-m", "baseline"], cwd=repo.root, check=True, capture_output=True)
        report_path = tmp_path / "spark-report.md"
        _json(
            run_cli(
                repo.root,
                "--json",
                "private",
                "spark",
                "report",
                "--month",
                "2026-07",
                "--output",
                str(report_path),
            )
        )
        status = subprocess.run(["git", "status", "--short"], cwd=repo.root, text=True, capture_output=True, check=True)
        assert status.stdout == ""
    finally:
        repo.close()


def test_migrate_private_spark_legacy_records():
    repo = TempRepository(SOURCE)
    try:
        path = repo.root / "data/private/spark/2026/2026-07.json"
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "type": "자위",
                            "at": "2026-07-05T03:40:00+09:00",
                            "text": "legacy memo",
                        },
                        {
                            "category": "섹스",
                            "partner": "someone",
                            "started_at": "2026-07-05T04:00:00+09:00",
                            "ended_at": "2026-07-05T04:20:00+09:00",
                        },
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        migrated = _json(run_cli(repo.root, "--json", "migrate"))
        assert migrated["private_spark"] == {"files": 1, "records": 3}
        store = json.loads(path.read_text(encoding="utf-8"))
        assert store["schema_version"] == 1
        assert store["records"][0]["kind"] == "solo"
        assert store["records"][0]["ended_at"] == "2026-07-05T03:40:00+09:00"
        assert store["records"][0]["note"] == "legacy memo"
        assert store["records"][1]["kind"] == "together"
        assert store["records"][1]["partner"] == "someone"
        assert all("id" in record and "created_at" in record and "updated_at" in record for record in store["records"])
        assert run_cli(repo.root, "--json", "validate").returncode == 0
        before = path.read_text(encoding="utf-8")
        migrated_again = _json(run_cli(repo.root, "--json", "migrate"))
        assert migrated_again["private_spark"] == {"files": 0, "records": 0}
        assert path.read_text(encoding="utf-8") == before
    finally:
        repo.close()
