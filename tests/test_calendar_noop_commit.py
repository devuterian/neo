from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from helpers import TempRepository


class CalendarNoopCommitTest(unittest.TestCase):
    """Calendar imports should not create commits when events haven't changed."""

    def setUp(self) -> None:
        self.repo = TempRepository(Path(__file__).resolve().parents[1])
        self._tmp_dir = self.repo.root.parent  # parent of repo root in temp
        subprocess.run(["git", "init", "-b", "main"], cwd=self.repo.root,
                       capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"],
                       cwd=self.repo.root, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                       cwd=self.repo.root, capture_output=True, check=True)

    def tearDown(self) -> None:
        self.repo.close()

    def _run(self, *args):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src") + os.pathsep + env.get("PYTHONPATH", "")
        return subprocess.run(
            [sys.executable, "-m", "neo.cli", *args],
            cwd=self.repo.root, env=env, text=True, capture_output=True,
        )

    def _commit_count(self) -> int:
        return int(subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=self.repo.root, capture_output=True, text=True, check=True,
        ).stdout.strip())

    def _base_payload(self):
        return {
            "schema_version": 1,
            "generated_at": "2026-07-03T10:00:00+09:00",
            "source": {
                "status": "available",
                "fetched_at": "2026-07-03T10:00:00+09:00",
                "range_start": "2026-07-03T00:00:00+09:00",
                "range_end": "2026-08-14T00:00:00+09:00",
                "error": None,
            },
            "events": {
                "cal1::evt1": {
                    "event_id": "evt1",
                    "calendar_id": "cal1",
                    "title": "치과",
                    "starts_at": "2026-07-17T10:00:00+09:00",
                    "ends_at": "2026-07-17T11:00:00+09:00",
                    "all_day": False,
                    "color_id": None,
                    "links": {
                        "event_type": "external",
                        "project_id": None,
                        "milestone_id": None,
                        "task_id": None,
                        "day_id": None,
                    },
                },
            },
        }

    def _write_and_import(self, payload, suffix):
        tmp = self._tmp_dir / f"cal-{suffix}.json"
        tmp.write_text(json.dumps(payload, ensure_ascii=False))
        result = self._run("--json", "calendar", "import-index", "--input", str(tmp))
        return result

    def test_calendar_import_same_payload_twice_does_not_create_second_commit(self) -> None:
        """Identical calendar data imported twice → only one commit."""
        payload = self._base_payload()
        r1 = self._write_and_import(payload, "first")
        self.assertEqual(r1.returncode, 0, f"First import failed: {r1.stderr}")
        count1 = self._commit_count()

        # Second import: same events, only timestamps changed
        payload["generated_at"] = "2026-07-03T11:00:00+09:00"
        payload["source"]["fetched_at"] = "2026-07-03T11:00:00+09:00"
        r2 = self._write_and_import(payload, "second")
        self.assertEqual(r2.returncode, 0, f"Second import failed: {r2.stderr}")
        count2 = self._commit_count()

        self.assertEqual(count1, count2,
                         f"Second import with identical events created a commit: {count1} → {count2}")

    def test_calendar_import_ignores_range_window_timestamp_only_changes(self) -> None:
        """Refresh with same events, different generated_at/range window → no commit."""
        payload = self._base_payload()
        r1 = self._write_and_import(payload, "first")
        self.assertEqual(r1.returncode, 0, f"First import failed: {r1.stderr}")
        count1 = self._commit_count()

        # Only change generated_at (simulating a refresh)
        payload["generated_at"] = "2026-07-04T10:00:00+09:00"
        payload["source"]["fetched_at"] = "2026-07-04T10:00:00+09:00"
        payload["source"]["range_start"] = "2026-07-04T00:00:00+09:00"
        payload["source"]["range_end"] = "2026-08-15T00:00:00+09:00"
        r2 = self._write_and_import(payload, "refresh")
        self.assertEqual(r2.returncode, 0, f"Refresh import failed: {r2.stderr}")
        count2 = self._commit_count()

        self.assertEqual(count1, count2,
                         f"Timestamp-only refresh created an extra commit: {count1} → {count2}")

    def test_calendar_import_with_one_new_event_creates_commit(self) -> None:
        """Adding a new event should still create a commit."""
        payload = self._base_payload()
        r1 = self._write_and_import(payload, "first")
        self.assertEqual(r1.returncode, 0, f"First import failed: {r1.stderr}")
        count1 = self._commit_count()

        # Add a genuinely new event
        payload["events"]["cal1::evt2"] = {
            "event_id": "evt2",
            "calendar_id": "cal1",
            "title": "병원",
            "starts_at": "2026-07-20T14:00:00+09:00",
            "ends_at": "2026-07-20T15:00:00+09:00",
            "all_day": False,
            "color_id": None,
            "links": {
                "event_type": "external",
                "project_id": None,
                "milestone_id": None,
                "task_id": None,
                "day_id": None,
            },
        }
        r2 = self._write_and_import(payload, "changed")
        self.assertEqual(r2.returncode, 0, f"Changed import failed: {r2.stderr}")
        count2 = self._commit_count()

        self.assertGreater(count2, count1,
                           f"Real event addition did NOT create a commit: {count1} → {count2}")

    def test_calendar_import_with_modified_event_creates_commit(self) -> None:
        """Modifying an existing event (title/time) should create a commit."""
        payload = self._base_payload()
        r1 = self._write_and_import(payload, "first")
        self.assertEqual(r1.returncode, 0, f"First import failed: {r1.stderr}")
        count1 = self._commit_count()

        # Modify existing event's title
        payload["events"]["cal1::evt1"]["title"] = "치과 재방문"
        r2 = self._write_and_import(payload, "modified")
        self.assertEqual(r2.returncode, 0, f"Modified import failed: {r2.stderr}")
        count2 = self._commit_count()

        self.assertGreater(count2, count1,
                           f"Real event modification did NOT create a commit: {count1} → {count2}")

    def test_calendar_import_with_removed_event_creates_commit(self) -> None:
        """Removing an event should create a commit."""
        payload = self._base_payload()
        r1 = self._write_and_import(payload, "first")
        self.assertEqual(r1.returncode, 0, f"First import failed: {r1.stderr}")
        count1 = self._commit_count()

        # Remove event
        del payload["events"]["cal1::evt1"]
        r2 = self._write_and_import(payload, "removed")
        self.assertEqual(r2.returncode, 0, f"Removed import failed: {r2.stderr}")
        count2 = self._commit_count()

        self.assertGreater(count2, count1,
                           f"Event removal did NOT create a commit: {count1} → {count2}")

    def test_calendar_import_preserves_same_event_id_from_two_calendars(self) -> None:
        payload = self._base_payload()
        payload["events"]["cal2::evt1"] = dict(payload["events"]["cal1::evt1"], calendar_id="cal2", title="다른 캘린더")
        r = self._write_and_import(payload, "collision")
        self.assertEqual(r.returncode, 0, r.stderr)
        saved = json.loads((self.repo.root / "data/indexes/calendar.json").read_text())
        self.assertIn("cal1::evt1", saved["events"])
        self.assertIn("cal2::evt1", saved["events"])
