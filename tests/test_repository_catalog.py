from __future__ import annotations

import json
import unittest
from pathlib import Path

from helpers import TempRepository
from neo.errors import ConflictError, NotFoundError
from neo.repository import ProjectLocation, Repository, TaskLocation
from neo.repository_catalog import (
    ProjectLocation as CatalogProjectLocation,
    TaskLocation as CatalogTaskLocation,
)


class RepositoryCatalogTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TempRepository(Path(__file__).resolve().parents[1])
        self._write_project(
            "alpha",
            project_id="project-alpha",
            title="Alpha",
            milestone_id="milestone-alpha",
            milestone_title="Production",
            task_id="task-alpha",
            task_title="Shared task",
        )
        self._write_project(
            "beta",
            project_id="project-beta",
            title="Beta",
            milestone_id="milestone-beta",
            milestone_title="Delivery",
            task_id="task-beta",
            task_title="Shared task",
        )
        self.repo = Repository(self.temp.paths)

    def tearDown(self) -> None:
        self.temp.close()

    def _write_project(
        self,
        slug: str,
        *,
        project_id: str,
        title: str,
        milestone_id: str,
        milestone_title: str,
        task_id: str,
        task_title: str,
    ) -> None:
        document = {
            "project_id": project_id,
            "slug": slug,
            "title": title,
            "milestones": [
                {
                    "milestone_id": milestone_id,
                    "title": milestone_title,
                    "tasks": [
                        {
                            "task_id": task_id,
                            "title": task_title,
                        }
                    ],
                }
            ],
        }
        path = self.temp.paths.projects / f"{slug}.json"
        path.write_text(
            json.dumps(document, ensure_ascii=False),
            encoding="utf-8",
        )

    def test_repository_keeps_location_compatibility_exports(self) -> None:
        self.assertIs(ProjectLocation, CatalogProjectLocation)
        self.assertIs(TaskLocation, CatalogTaskLocation)

    def test_catalog_lookup_maps_are_read_only(self) -> None:
        catalog = self.repo.load_catalog()
        with self.assertRaises(TypeError):
            catalog.project_by_exact_token["other"] = catalog.projects[0]  # type: ignore[index]
        with self.assertRaises(TypeError):
            catalog.scoped_task_by_id["project-alpha"]["other"] = (  # type: ignore[index]
                catalog.resolve_task("task-alpha")
            )

    def test_resolves_projects_by_id_slug_and_casefolded_title(self) -> None:
        self.assertEqual(
            self.repo.resolve_project("project-alpha").data["slug"],
            "alpha",
        )
        self.assertEqual(
            self.repo.resolve_project("beta").data["project_id"],
            "project-beta",
        )
        self.assertEqual(
            self.repo.resolve_project("ALPHA").data["project_id"],
            "project-alpha",
        )

    def test_resolves_task_id_without_loading_projects_twice(self) -> None:
        calls = 0
        original = self.repo.load_projects

        def counted_load_projects():
            nonlocal calls
            calls += 1
            return original()

        self.repo.load_projects = counted_load_projects  # type: ignore[method-assign]
        location = self.repo.resolve_task("task-beta")

        self.assertEqual(location.project["project_id"], "project-beta")
        self.assertEqual(calls, 1)

    def test_task_title_ambiguity_and_project_scope_match_previous_contract(self) -> None:
        with self.assertRaisesRegex(ConflictError, "Task title is ambiguous"):
            self.repo.resolve_task("shared task")

        location = self.repo.resolve_task("shared task", "alpha")
        self.assertEqual(location.task["task_id"], "task-alpha")

    def test_milestone_resolution_is_preserved(self) -> None:
        project = self.repo.resolve_project("alpha").data
        self.assertEqual(
            self.repo.resolve_milestone(project, "PRODUCTION")["milestone_id"],
            "milestone-alpha",
        )
        with self.assertRaisesRegex(NotFoundError, "Milestone not found"):
            self.repo.resolve_milestone(project, "missing")

    def test_exact_slug_precedes_an_ambiguous_title(self) -> None:
        self._write_project(
            "gamma",
            project_id="project-gamma",
            title="Alpha",
            milestone_id="milestone-gamma",
            milestone_title="Review",
            task_id="task-gamma",
            task_title="Unique task",
        )
        self.assertEqual(
            self.repo.resolve_project("alpha").data["project_id"],
            "project-alpha",
        )
        with self.assertRaisesRegex(ConflictError, "Project title is ambiguous"):
            self.repo.resolve_project("ALPHA")


if __name__ == "__main__":
    unittest.main()
