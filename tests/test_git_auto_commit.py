from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from neo.workspace import _git_commit, commit_workspace
from neo.domain.days import create_day, set_capacity

from helpers import TempRepository


class GitAutoCommitTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = TempRepository(Path(__file__).resolve().parents[1])
        subprocess.run(["git", "init", "-b", "main"], cwd=self.repo.root,
                       capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"],
                       cwd=self.repo.root, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                       cwd=self.repo.root, capture_output=True, check=True)

    def tearDown(self) -> None:
        self.repo.close()

    # ── no-op guards ────────────────────────────────────────

    def test_noop_when_no_git_dir(self) -> None:
        (self.repo.root / ".git").rename(self.repo.root / ".git_bak")
        try:
            result = _git_commit(
                self.repo.paths,
                created_or_modified=[self.repo.root / "day.json"],
                deleted=set(),
            )
            self.assertIsNone(result)
        finally:
            (self.repo.root / ".git_bak").rename(self.repo.root / ".git")

    def test_noop_when_no_paths(self) -> None:
        result = _git_commit(self.repo.paths, created_or_modified=[], deleted=set())
        self.assertIsNone(result)
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=self.repo.root, capture_output=True, text=True,
        )
        self.assertEqual(log.returncode, 128)

    # ── prefix correctness ──────────────────────────────────

    def test_commits_created_files_with_correct_prefix(self) -> None:
        p = self.repo.paths.projects / "alpha.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}", encoding="utf-8")
        _git_commit(self.repo.paths, created_or_modified=[p], deleted=set())
        log = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=self.repo.root, capture_output=True, text=True, check=True,
        )
        self.assertEqual(log.stdout.strip(), "neoctl: project")

    def test_commits_day_files_with_correct_prefix(self) -> None:
        p = self.repo.paths.days / "2026" / "2026-07-03.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}", encoding="utf-8")
        _git_commit(self.repo.paths, created_or_modified=[p], deleted=set())
        log = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=self.repo.root, capture_output=True, text=True, check=True,
        )
        self.assertEqual(log.stdout.strip(), "neoctl: day")

    def test_commits_multiple_domains_with_combined_prefix(self) -> None:
        p1 = self.repo.paths.projects / "alpha.json"
        p1.parent.mkdir(parents=True, exist_ok=True)
        p1.write_text("{}", encoding="utf-8")
        p2 = self.repo.paths.days / "2026" / "2026-07-03.json"
        p2.parent.mkdir(parents=True, exist_ok=True)
        p2.write_text("{}", encoding="utf-8")
        _git_commit(self.repo.paths, created_or_modified=[p1, p2], deleted=set())
        log = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=self.repo.root, capture_output=True, text=True, check=True,
        )
        self.assertEqual(log.stdout.strip(), "neoctl: day, project")

    def test_commits_deleted_paths(self) -> None:
        p = self.repo.paths.projects / "stale.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}", encoding="utf-8")
        subprocess.run(["git", "add", str(p)], cwd=self.repo.root, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=self.repo.root, capture_output=True)
        p.unlink()
        _git_commit(self.repo.paths, created_or_modified=[], deleted={p})
        log = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=self.repo.root, capture_output=True, text=True, check=True,
        )
        self.assertEqual(log.stdout.strip(), "neoctl: project")

    def test_commit_message_for_brief(self) -> None:
        p = self.repo.paths.brief
        p.write_text("---", encoding="utf-8")
        _git_commit(self.repo.paths, created_or_modified=[p], deleted=set())
        log = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=self.repo.root, capture_output=True, text=True, check=True,
        )
        self.assertEqual(log.stdout.strip(), "neoctl: brief")

    def test_commit_message_for_config(self) -> None:
        p = self.repo.paths.root / "config" / "app.json"
        p.write_text("{}", encoding="utf-8")
        _git_commit(self.repo.paths, created_or_modified=[p], deleted=set())
        log = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=self.repo.root, capture_output=True, text=True, check=True,
        )
        self.assertEqual(log.stdout.strip(), "neoctl: config")

    # ── edge cases ──────────────────────────────────────────

    def test_handles_paths_outside_repo_gracefully(self) -> None:
        outside = Path("/tmp/ghost.json")
        outside.write_text("{}", encoding="utf-8")
        initial_commits = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=self.repo.root, capture_output=True, text=True,
        )
        try:
            _git_commit(self.repo.paths, created_or_modified=[outside], deleted=set())
        finally:
            outside.unlink(missing_ok=True)
        final_commits = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=self.repo.root, capture_output=True, text=True,
        )
        self.assertEqual(initial_commits.stdout.strip(), final_commits.stdout.strip())

    def test_mixed_inside_and_outside_paths_handled(self) -> None:
        inside = self.repo.paths.projects / "alpha.json"
        inside.parent.mkdir(parents=True, exist_ok=True)
        inside.write_text("{}", encoding="utf-8")
        outside = Path("/tmp/ghost2.json")
        outside.write_text("{}", encoding="utf-8")
        try:
            _git_commit(self.repo.paths, created_or_modified=[inside, outside], deleted=set())
        finally:
            outside.unlink(missing_ok=True)
        log = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=self.repo.root, capture_output=True, text=True, check=True,
        )
        self.assertIn("project", log.stdout.strip())

    def test_handles_git_add_failure_gracefully(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(128, "git add")
            result = _git_commit(
                self.repo.paths,
                created_or_modified=[self.repo.root / "day.json"],
                deleted=set(),
            )
            self.assertIsNone(result)

    # ── no-duplicate-commit guards ──────────────────────────

    def test_no_commit_when_no_staged_changes(self) -> None:
        p = self.repo.paths.projects / "alpha.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}", encoding="utf-8")
        _git_commit(self.repo.paths, created_or_modified=[p], deleted=set())
        commit_count_before = len(subprocess.run(
            ["git", "log", "--oneline"],
            cwd=self.repo.root, capture_output=True, text=True, check=True,
        ).stdout.strip().splitlines())
        _git_commit(self.repo.paths, created_or_modified=[p], deleted=set())
        commit_count_after = len(subprocess.run(
            ["git", "log", "--oneline"],
            cwd=self.repo.root, capture_output=True, text=True, check=True,
        ).stdout.strip().splitlines())
        self.assertEqual(commit_count_before, commit_count_after)

    # ── PROBLEM 1 regression ────────────────────────────────

    def test_auto_commit_does_not_include_preexisting_staged_unrelated_file(self) -> None:
        """Pre-existing staged files outside neoctl pathspec are NOT committed."""
        unrelated = self.repo.root / "unrelated.txt"
        unrelated.write_text("pre-staged content")
        subprocess.run(["git", "add", str(unrelated)], cwd=self.repo.root,
                       capture_output=True, check=True)

        brief = self.repo.paths.brief
        brief.write_text("neoctl-triggered change")
        _git_commit(self.repo.paths, created_or_modified=[brief], deleted=set())

        # Verify unrelated.txt is NOT in the commit
        committed_files = subprocess.run(
            ["git", "log", "-1", "--name-only", "--format="],
            cwd=self.repo.root, capture_output=True, text=True, check=True,
        ).stdout.strip().splitlines()
        committed_files = [f.strip() for f in committed_files if f.strip()]
        self.assertNotIn("unrelated.txt", committed_files,
                         f"unrelated.txt was included in auto-commit: {committed_files}")

        # unrelated.txt should still be staged, not consumed
        status = subprocess.run(
            ["git", "status", "--short", "--", "unrelated.txt"],
            cwd=self.repo.root, capture_output=True, text=True,
        ).stdout
        self.assertIn("unrelated.txt", status,
                      "unrelated.txt should still be tracked in git status")

    def test_auto_commit_pathspec_isolates_from_other_staged_files(self) -> None:
        """Multiple pre-staged files remain untouched; only neoctl paths committed."""
        for name in ["a.txt", "b.txt", "c.txt"]:
            f = self.repo.root / name
            f.write_text(f"pre-{name}")
            subprocess.run(["git", "add", str(f)], cwd=self.repo.root,
                           capture_output=True, check=True)

        proj = self.repo.paths.projects / "proj.json"
        proj.parent.mkdir(parents=True, exist_ok=True)
        proj.write_text("{}", encoding="utf-8")
        day = self.repo.paths.days / "2026" / "2026-07-03.json"
        day.parent.mkdir(parents=True, exist_ok=True)
        day.write_text("{}", encoding="utf-8")

        _git_commit(self.repo.paths, created_or_modified=[proj, day], deleted=set())

        committed = subprocess.run(
            ["git", "log", "-1", "--name-only", "--format="],
            cwd=self.repo.root, capture_output=True, text=True, check=True,
        ).stdout.strip().splitlines()
        committed = [f.strip() for f in committed if f.strip()]

        for name in ["a.txt", "b.txt", "c.txt"]:
            self.assertNotIn(name, committed,
                             f"{name} should not be in neo auto-commit")

        for name in ["a.txt", "b.txt", "c.txt"]:
            status = subprocess.run(
                ["git", "status", "--short", "--", name],
                cwd=self.repo.root, capture_output=True, text=True,
            ).stdout
            self.assertIn(name, status,
                          f"{name} should still be staged")

    # ── integration ────────────────────────────────────────

    def test_commit_workspace_triggers_git_commit(self) -> None:
        day = create_day("2026-07-03T19:42:00+09:00")
        day = set_capacity(day, 1.0)
        day_path = self.repo.paths.days / "2026" / "2026-07-03.json"

        commit_workspace(self.repo.paths, day_updates={day_path: day})

        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=self.repo.root, capture_output=True, text=True, check=True,
        )
        self.assertIn("neoctl:", log.stdout)
        self.assertTrue(day_path.exists())

    def test_commit_workspace_without_git_does_not_crash(self) -> None:
        (self.repo.root / ".git").rename(self.repo.root / ".git_bak")
        try:
            day = create_day("2026-07-03T19:42:00+09:00")
            day_path = self.repo.paths.days / "2026" / "2026-07-03.json"
            commit_workspace(self.repo.paths, day_updates={day_path: day})
            self.assertTrue(day_path.exists())
        finally:
            (self.repo.root / ".git_bak").rename(self.repo.root / ".git")

    def test_commit_failure_records_status_and_skips_push(self) -> None:
        p = self.repo.paths.brief
        p.write_text("neoctl-triggered change", encoding="utf-8")
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            if cmd[:2] == ["git", "add"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
            if cmd[:3] == ["git", "diff", "--cached"]:
                return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")
            if cmd[:2] == ["git", "commit"]:
                return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="commit failed")
            if cmd[:3] == ["git", "branch", "--show-current"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="main\n", stderr="")
            if cmd[:2] == ["git", "push"]:
                self.fail("git push must not be called when git commit fails")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=fake_run):
            _git_commit(self.repo.paths, created_or_modified=[p], deleted=set())

        status = __import__("json").loads(self.repo.paths.last_push.read_text(encoding="utf-8"))
        self.assertFalse(status["success"])
        self.assertEqual(status["remote"], "origin")
        self.assertEqual(status["branch"], "main")
        self.assertEqual(status["error"], "commit failed")
        self.assertFalse(any(call[:2] == ["git", "push"] for call in calls))
