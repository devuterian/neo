from __future__ import annotations

import unittest
from pathlib import Path

from neo.git_sync import _commit_subject, _git_commit, sync_runtime_changes
from neo.workspace import _git_commit as workspace_git_commit
from neo.workspace import _validate_cross_references
from neo.workspace_changes import WorkspaceChangeSet
from neo.workspace_validation import validate_cross_references


class WorkspaceBoundaryTest(unittest.TestCase):
    def test_change_set_copies_mutable_inputs(self) -> None:
        project_path = Path("project.json")
        projects = {project_path: {"project_id": "project"}}
        deletes = {Path("stale.json")}

        changes = WorkspaceChangeSet.from_updates(
            project_updates=projects,
            delete_paths=deletes,
        )
        projects.clear()
        deletes.clear()

        self.assertIn(project_path, changes.project_updates)
        self.assertEqual(changes.delete_paths, {Path("stale.json")})

    def test_workspace_keeps_git_compatibility_export(self) -> None:
        self.assertIs(workspace_git_commit, _git_commit)
        self.assertTrue(callable(sync_runtime_changes))

    def test_workspace_keeps_cross_validation_compatibility_export(self) -> None:
        self.assertIs(_validate_cross_references, validate_cross_references)

    def test_commit_subject_preserves_domain_order(self) -> None:
        subject = _commit_subject(
            [
                "data/projects/sample.json",
                "brief.md",
                "data/days/2026/2026-07-10.json",
            ]
        )
        self.assertEqual(subject, "neoctl: brief, day, project")


if __name__ == "__main__":
    unittest.main()
