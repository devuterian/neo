from __future__ import annotations

import unittest
from pathlib import Path

from neo.domain.days import check_in, check_out, create_day, plan_task, set_capacity
from neo.domain.projects import add_milestone, add_task, create_project, set_project_status, set_task_status
from neo.validation import validate_all
from neo.workspace import commit_workspace

from helpers import TempRepository


class DayStorageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = TempRepository(Path(__file__).resolve().parents[1])

    def tearDown(self) -> None:
        self.repo.close()

    def test_day_references_task_and_tracks_session(self) -> None:
        project = create_project("Project Alpha", "project-alpha")
        project, milestone_id = add_milestone(project, "First draft", 2.0)
        project, task_id = add_task(project, milestone_id, "Prepare scenes")
        project = set_project_status(project, "active")
        milestone = project["milestones"][0]
        task = milestone["tasks"][0]

        day = create_day("2026-07-03T19:42:00+09:00")
        day = set_capacity(day, 0.5)
        day = plan_task(
            day,
            project=project,
            milestone=milestone,
            task=task,
            allocation=0.5,
        )
        day, session_id = check_in(
            day,
            project=project,
            milestone=milestone,
            task=task,
            at="2026-07-03T23:00:00+09:00",
        )
        day = check_out(day, session_id, "2026-07-04T02:00:00+09:00", "done")
        project = set_task_status(project, task_id, "done")

        project_path = self.repo.paths.projects / "project-alpha.json"
        day_path = self.repo.paths.days / "2026" / "2026-07-03.json"
        commit_workspace(
            self.repo.paths,
            project_updates={project_path: project},
            day_updates={day_path: day},
        )

        self.assertTrue(day_path.exists())
        self.assertIn("Project Alpha", self.repo.paths.brief.read_text(encoding="utf-8"))
        self.assertFalse([issue for issue in validate_all(self.repo.paths) if issue.severity == "error"])


if __name__ == "__main__":
    unittest.main()
