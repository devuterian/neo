from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from neo.paths import NeoPaths


_SEED_CURRENT = {
    "schema_version": 1,
    "generated_at": None,
    "current_day": None,
    "current_work_session": None,
}

_SEED_PROJECTS = {
    "schema_version": 1,
    "generated_at": None,
    "projects": [],
}

_SEED_CALENDAR = {
    "schema_version": 1,
    "generated_at": None,
    "source": {
        "status": "not_configured",
        "fetched_at": None,
        "range_start": None,
        "range_end": None,
        "error": None,
    },
    "events": {},
}


class TempRepository:
    def __init__(self, source_root: Path):
        self._temp = tempfile.TemporaryDirectory()
        self.root = Path(self._temp.name) / "repo"
        self.root.mkdir()
        # Copy only config and schemas – NOT data (test data must be isolated).
        for name in ["config", "schemas"]:
            shutil.copytree(source_root / name, self.root / name)
        shutil.copyfile(
            self.root / "config" / "app.example.json",
            self.root / "config" / "app.json",
        )
        # Build empty but valid data/ tree (no real user data).
        self.root.joinpath(".neo/transactions").mkdir(parents=True)
        indexes_dir = self.root.joinpath("data/indexes")
        indexes_dir.mkdir(parents=True)
        (indexes_dir / "current.json").write_text(json.dumps(_SEED_CURRENT, ensure_ascii=False))
        (indexes_dir / "projects.json").write_text(json.dumps(_SEED_PROJECTS, ensure_ascii=False))
        (indexes_dir / "calendar.json").write_text(json.dumps(_SEED_CALENDAR, ensure_ascii=False))
        (self.root / "data" / "projects").mkdir(parents=True, exist_ok=True)
        (self.root / "data" / "days").mkdir(parents=True, exist_ok=True)
        (self.root / "brief.md").write_text("", encoding="utf-8")
        self.paths = NeoPaths(self.root)

    def close(self) -> None:
        self._temp.cleanup()


def run_cli(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["TZ"] = "Asia/Seoul"
    src = Path(__file__).resolve().parents[1] / "src"
    env["PYTHONPATH"] = str(src) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "neo.cli", *args],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
