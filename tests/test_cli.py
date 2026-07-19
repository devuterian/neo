from __future__ import annotations

import unittest
from pathlib import Path

from helpers import TempRepository, run_cli


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = TempRepository(Path(__file__).resolve().parents[1])

    def tearDown(self) -> None:
        self.repo.close()

    def test_project_creation_requires_approval(self) -> None:
        result = run_cli(self.repo.root,
            "project", "create", "--title", "Test", "--slug", "test"
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("requires explicit operator approval", result.stderr)

    def test_wake_uses_wake_date_as_filename(self) -> None:
        result = run_cli(self.repo.root,
            "day", "wake", "--at", "2026-07-03T19:42:00+09:00"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(
            (self.repo.paths.days / "2026" / "2026-07-03.json").exists()
        )

    def test_second_wake_on_same_calendar_date_is_rejected(self) -> None:
        first = run_cli(self.repo.root,
            "day", "wake", "--at", "2026-07-03T19:42:00+09:00"
        )
        self.assertEqual(first.returncode, 0, first.stderr)
        second = run_cli(self.repo.root,
            "day", "wake", "--at", "2026-07-03T23:30:00+09:00"
        )
        self.assertEqual(second.returncode, 2)
        self.assertIn("already exists for wake date", second.stderr)

    def test_next_wake_closes_previous_life_day(self) -> None:
        first = run_cli(self.repo.root,
            "day", "wake", "--at", "2026-07-03T19:42:00+09:00"
        )
        self.assertEqual(first.returncode, 0, first.stderr)
        second = run_cli(self.repo.root,
            "day", "wake", "--at", "2026-07-04T18:00:00+09:00"
        )
        self.assertEqual(second.returncode, 0, second.stderr)
        import json
        previous = json.loads(
            (self.repo.paths.days / "2026" / "2026-07-03.json").read_text(encoding="utf-8")
        )
        self.assertEqual(previous["status"], "closed")
        self.assertEqual(previous["closed_at"], "2026-07-04T18:00:00+09:00")


if __name__ == "__main__":
    unittest.main()
