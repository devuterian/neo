from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from helpers import TempRepository
from neo.migrate import CATEGORY_MAP, calendar_key, migrate_state
from neo.migration_steps import (
    migrate_calendar_index,
    migrate_day_document,
    migrate_fridge_document,
)


class MigrationStepTest(unittest.TestCase):
    def test_day_migration_is_non_mutating_and_idempotent(self) -> None:
        source = {
            "day_id": "day-1",
            "updated_at": "old",
            "custom": {"preserved": True},
        }
        first = migrate_day_document(source, timestamp="2026-07-10T12:00:00+09:00")

        self.assertTrue(first.changed)
        self.assertNotIn("medications", source)
        self.assertIn("medications", first.document)
        self.assertEqual(first.document["updated_at"], "2026-07-10T12:00:00+09:00")
        self.assertEqual(first.document["custom"], {"preserved": True})

        second = migrate_day_document(
            first.document,
            timestamp="2026-07-11T12:00:00+09:00",
        )
        self.assertFalse(second.changed)
        self.assertEqual(second.document, first.document)

    def test_calendar_migration_rekeys_once_and_preserves_fields(self) -> None:
        source = {
            "generated_at": "old",
            "source": {"status": "ok"},
            "events": {
                "event-1": {
                    "calendar_id": "calendar-a",
                    "event_id": "event-1",
                    "title": "Sample",
                }
            },
        }
        first = migrate_calendar_index(
            source,
            timestamp="2026-07-10T12:00:00+09:00",
        )

        self.assertTrue(first.changed)
        self.assertIn("event-1", source["events"])
        self.assertIn("calendar-a::event-1", first.document["events"])
        self.assertEqual(first.document["source"], {"status": "ok"})
        self.assertEqual(first.document["generated_at"], "2026-07-10T12:00:00+09:00")

        second = migrate_calendar_index(
            first.document,
            timestamp="2026-07-11T12:00:00+09:00",
        )
        self.assertFalse(second.changed)
        self.assertEqual(second.document, first.document)

    def test_fridge_migration_maps_legacy_and_unknown_categories_once(self) -> None:
        source = {
            "updated_at": "old",
            "items": [
                {"item_id": "1", "category": "protein"},
                {"item_id": "2", "category": "snack"},
                {"item_id": "3", "category": "legacy-unknown"},
            ],
        }
        first = migrate_fridge_document(
            source,
            timestamp="2026-07-10T12:00:00+09:00",
        )

        self.assertTrue(first.changed)
        self.assertEqual(
            [item["category"] for item in first.document["items"]],
            ["ingredient", "snack", "other"],
        )
        self.assertEqual(source["items"][0]["category"], "protein")

        second = migrate_fridge_document(
            first.document,
            timestamp="2026-07-11T12:00:00+09:00",
        )
        self.assertFalse(second.changed)
        self.assertEqual(second.document, first.document)

    def test_migrate_module_keeps_compatibility_exports(self) -> None:
        self.assertEqual(calendar_key("calendar", "event"), "calendar::event")
        self.assertEqual(CATEGORY_MAP["protein"], "ingredient")


class MigrationOrchestrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = TempRepository(Path(__file__).resolve().parents[1])

    def tearDown(self) -> None:
        self.repo.close()

    def test_no_canonical_change_skips_workspace_commit(self) -> None:
        with (
            patch("neo.migrate.commit_workspace") as commit,
            patch(
                "neo.migrate.spark_domain.migrate_legacy_records",
                return_value={"changed": False},
            ),
        ):
            result = migrate_state(self.repo.paths)

        commit.assert_not_called()
        self.assertEqual(result["days"], 0)
        self.assertFalse(result["calendar"])
        self.assertFalse(result["fridge"])

    def test_changed_documents_are_batched_into_one_workspace_commit(self) -> None:
        day_path = self.repo.paths.days / "2026" / "2026-07-10.json"
        day_path.parent.mkdir(parents=True, exist_ok=True)
        day_path.write_text(
            json.dumps(
                {
                    "day_id": "day-1",
                    "date": "2026-07-10",
                    "updated_at": "old",
                }
            ),
            encoding="utf-8",
        )

        with (
            patch("neo.migrate.now_iso", return_value="2026-07-10T12:00:00+09:00"),
            patch("neo.migrate.commit_workspace") as commit,
            patch(
                "neo.migrate.spark_domain.migrate_legacy_records",
                return_value={"changed": False},
            ),
        ):
            result = migrate_state(self.repo.paths)

        self.assertEqual(result["days"], 1)
        commit.assert_called_once()
        updates = commit.call_args.kwargs["day_updates"]
        self.assertEqual(set(updates), {day_path})
        self.assertIn("medications", updates[day_path])


if __name__ == "__main__":
    unittest.main()
