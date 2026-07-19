from __future__ import annotations

import unittest
from pathlib import Path

from neo.domain.projects import create_project
from neo.validation import schema_issues

from helpers import TempRepository


class ValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = TempRepository(Path(__file__).resolve().parents[1])

    def tearDown(self) -> None:
        self.repo.close()

    def test_project_rejects_local_deadline_date(self) -> None:
        project = create_project("Test", "test")
        project["deadline_at"] = "2026-07-10T18:00:00+09:00"
        issues = schema_issues(
            self.repo.paths, project, "project.schema.json", "project"
        )
        self.assertTrue(any("Additional properties" in issue.message for issue in issues))

    def test_capacity_rejects_unapproved_value(self) -> None:
        from neo.domain.days import create_day

        day = create_day("2026-07-03T19:00:00+09:00")
        day["workday_capacity"] = 0.25
        issues = schema_issues(self.repo.paths, day, "day.schema.json", "day")
        self.assertTrue(issues)


if __name__ == "__main__":
    unittest.main()
