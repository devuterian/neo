from __future__ import annotations

import unittest
from pathlib import Path

from neo.domain.projects import add_milestone, add_task, create_project, set_project_status
from neo.validation import validate_all
from neo.workspace import commit_workspace

from helpers import TempRepository


class ProjectStorageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = TempRepository(Path(__file__).resolve().parents[1])

    def tearDown(self) -> None:
        self.repo.close()

    def test_project_milestone_task_hierarchy(self) -> None:
        project = create_project("테스트 프로젝트", "test-project")
        project, milestone_id = add_milestone(project, "첫 마일스톤", 1.5)
        project, task_id = add_task(project, milestone_id, "러프 구성")
        project = set_project_status(project, "active", reason="start")
        path = self.repo.paths.projects / "test-project.json"
        commit_workspace(self.repo.paths, project_updates={path: project})

        self.assertTrue(path.exists())
        self.assertEqual(project["milestones"][0]["tasks"][0]["task_id"], task_id)
        self.assertFalse([issue for issue in validate_all(self.repo.paths) if issue.severity == "error"])


if __name__ == "__main__":
    unittest.main()
