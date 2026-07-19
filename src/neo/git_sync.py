from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .paths import NeoPaths


@dataclass(frozen=True, slots=True)
class GitSyncResult:
    attempted: bool
    committed: bool
    pushed: bool | None
    branch: str | None = None
    error: str | None = None


def sync_runtime_changes(
    paths: NeoPaths,
    created_or_modified: list[Path],
    deleted: set[Path],
) -> GitSyncResult:
    root = paths.root
    if not (root / ".git").is_dir():
        return GitSyncResult(attempted=False, committed=False, pushed=None)

    relative_paths = _relative_paths(root, created_or_modified, deleted)
    if not relative_paths:
        return GitSyncResult(attempted=False, committed=False, pushed=None)

    try:
        subprocess.run(
            ["git", "add", "--", *relative_paths],
            cwd=root,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        return GitSyncResult(
            attempted=True,
            committed=False,
            pushed=None,
            error=_short_subprocess_error(exc),
        )

    try:
        diff_proc = subprocess.run(
            ["git", "diff", "--cached", "--quiet", "--", *relative_paths],
            cwd=root,
            capture_output=True,
        )
        if diff_proc.returncode == 0:
            return GitSyncResult(attempted=True, committed=False, pushed=None)
    except subprocess.CalledProcessError:
        pass

    commit_proc = subprocess.run(
        ["git", "commit", "-m", _commit_subject(relative_paths), "--", *relative_paths],
        cwd=root,
        capture_output=True,
        text=True,
    )
    branch_proc = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    branch = branch_proc.stdout.strip() or "main"

    if commit_proc.returncode != 0:
        error = _short_subprocess_error(commit_proc)
        _record_push_status(
            paths,
            remote="origin",
            branch=branch,
            success=False,
            error=error,
        )
        return GitSyncResult(
            attempted=True,
            committed=False,
            pushed=False,
            branch=branch,
            error=error,
        )

    push_proc = subprocess.run(
        ["git", "push", "origin", branch],
        cwd=root,
        capture_output=True,
        text=True,
    )
    pushed = push_proc.returncode == 0
    error = _short_subprocess_error(push_proc) if not pushed else None
    _record_push_status(
        paths,
        remote="origin",
        branch=branch,
        success=pushed,
        error=error,
    )
    return GitSyncResult(
        attempted=True,
        committed=True,
        pushed=pushed,
        branch=branch,
        error=error,
    )


def _git_commit(paths: NeoPaths, created_or_modified: list[Path], deleted: set[Path]) -> None:
    """Compatibility wrapper retained for existing internal imports and tests."""

    sync_runtime_changes(paths, created_or_modified, deleted)


def _relative_paths(root: Path, created_or_modified: list[Path], deleted: set[Path]) -> list[str]:
    root_resolved = root.resolve()
    relative_paths: list[str] = []
    for path in [*created_or_modified, *deleted]:
        try:
            relative_paths.append(path.resolve().relative_to(root_resolved).as_posix())
        except ValueError:
            continue
    return relative_paths


def _commit_subject(relative_paths: list[str]) -> str:
    touched: set[str] = set()
    for relative_path in relative_paths:
        parts = relative_path.split("/")
        if parts[0] == "data" and len(parts) > 1:
            if parts[1] == "projects" and len(parts) == 3:
                touched.add("project")
            elif parts[1] == "days" and len(parts) == 4:
                touched.add("day")
            elif parts[1] == "indexes":
                touched.add("index")
            elif relative_path == "data/medical.json":
                touched.add("medical")
            elif relative_path == "data/pending.json":
                touched.add("pending")
            elif parts[1:3] == ["private", "spark"]:
                touched.add("private-spark")
        elif relative_path == "brief.md":
            touched.add("brief")
        elif relative_path == "config/app.json":
            touched.add("config")

    domains = sorted(touched)
    return "neoctl: " + ", ".join(domains) if domains else "neoctl: data change"


def _short_subprocess_error(
    proc: subprocess.CompletedProcess[str] | subprocess.CalledProcessError,
) -> str | None:
    stderr = getattr(proc, "stderr", None)
    stdout = getattr(proc, "stdout", None)
    lines = (stderr or stdout or "").strip().splitlines()
    return lines[-1] if lines else None


def _record_push_status(
    paths: NeoPaths,
    *,
    remote: str,
    branch: str,
    success: bool,
    error: str | None = None,
) -> None:
    payload = {
        "timestamp": __import__("neo.utils", fromlist=["now_iso"]).now_iso(),
        "success": success,
        "remote": remote,
        "branch": branch,
        "error": error if not success else None,
    }
    paths.runtime.mkdir(parents=True, exist_ok=True)
    paths.last_push.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
