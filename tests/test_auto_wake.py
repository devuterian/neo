from __future__ import annotations

import json
import unittest
from pathlib import Path

from neo.cli import resolve_day_or_auto_wake
from neo.errors import AutoWakeRejectedError
from neo.repository import Repository
from neo.workspace import commit_workspace
from neo.domain.days import create_day

from helpers import TempRepository, run_cli


class AutoWakeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = TempRepository(Path(__file__).resolve().parents[1])

    def tearDown(self) -> None:
        self.repo.close()

    # ── policy: ask (default) ──────────────────────────────────────

    def test_ask_policy_rejects_with_clear_message(self) -> None:
        """When auto_wake='ask' and no active day, reject with guidance."""
        repo = Repository(self.repo.paths)
        current = json.loads(self.repo.paths.current_index.read_text())
        self.assertIsNone(current.get("current_day"))

        with self.assertRaises(AutoWakeRejectedError) as ctx:
            resolve_day_or_auto_wake(repo, self.repo.paths)
        self.assertIn("No active life day", str(ctx.exception))
        self.assertIn("ask the user", str(ctx.exception))

    def test_ask_policy_via_cli(self) -> None:
        """Running 'day note' without active day + default ask policy errors."""
        result = run_cli(self.repo.root, "day", "note", "--text", "test")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No active life day", result.stderr)
        # No day file should have been created
        day_files = list(self.repo.paths.days.glob("*/*.json"))
        self.assertEqual(len(day_files), 0)

    # ── policy: always ─────────────────────────────────────────────

    def test_always_policy_creates_day(self) -> None:
        """When auto_wake='always', auto-create."""
        repo = Repository(self.repo.paths)
        path, day = resolve_day_or_auto_wake(repo, self.repo.paths, auto_wake_flag="always")
        self.assertIsNotNone(path)
        self.assertEqual(day["status"], "active")
        self.assertTrue(path.exists())

    def test_always_policy_via_cli_flag(self) -> None:
        """--auto-wake always flag overrides config."""
        result = run_cli(self.repo.root, "--auto-wake", "always", "day", "capacity", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        day_files = list(self.repo.paths.days.glob("*/*.json"))
        self.assertEqual(len(day_files), 1)
        day = json.loads(day_files[0].read_text())
        self.assertEqual(day["workday_capacity"], 1.0)

    def test_always_policy_reuses_existing_active_day(self) -> None:
        """When active day exists, always policy just returns it."""
        repo = Repository(self.repo.paths)
        day = create_day("2026-07-03T19:42:00+09:00")
        path = self.repo.paths.days / "2026" / "2026-07-03.json"
        commit_workspace(self.repo.paths, day_updates={path: day})

        result_path, result_day = resolve_day_or_auto_wake(repo, self.repo.paths, auto_wake_flag="always")
        self.assertEqual(result_path, path)
        self.assertEqual(result_day["day_id"], day["day_id"])

    # ── policy: never ──────────────────────────────────────────────

    def test_never_policy_rejects(self) -> None:
        """When auto_wake='never', hard reject."""
        repo = Repository(self.repo.paths)
        with self.assertRaises(AutoWakeRejectedError) as ctx:
            resolve_day_or_auto_wake(repo, self.repo.paths, auto_wake_flag="never")
        self.assertIn("never", str(ctx.exception))

    # ── regression: existing active day still works under any policy

    def test_active_day_works_regardless_of_policy(self) -> None:
        """When there IS an active day, resolve returns it regardless of policy."""
        repo = Repository(self.repo.paths)
        day = create_day("2026-07-03T19:42:00+09:00")
        path = self.repo.paths.days / "2026" / "2026-07-03.json"
        commit_workspace(self.repo.paths, day_updates={path: day})

        for flag in [None, "ask", "never", "always"]:
            with self.subTest(flag=flag):
                p, d = resolve_day_or_auto_wake(repo, self.repo.paths, auto_wake_flag=flag)
                self.assertEqual(d["day_id"], day["day_id"])

    # ── calendar operations (no day needed) ────────────────────────

    def test_calendar_import_index_works_without_active_day(self) -> None:
        """calendar import-index works regardless of life day state."""
        index = {
            "schema_version": 1,
            "generated_at": "2026-07-03T12:00:00+09:00",
            "source": {
                "status": "available",
                "fetched_at": "2026-07-03T12:00:00+09:00",
                "range_start": "2026-07-03T00:00:00+09:00",
                "range_end": "2026-08-14T00:00:00+09:00",
                "error": None,
            },
            "events": {},
        }
        tmp_path = Path("/tmp/neo-test-calendar-index.json")
        tmp_path.write_text(json.dumps(index, ensure_ascii=False))
        try:
            result = run_cli(
                self.repo.root, "calendar", "import-index", "--input", str(tmp_path)
            )
            self.assertEqual(result.returncode, 0, result.stderr)
        finally:
            tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
