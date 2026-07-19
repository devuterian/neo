from __future__ import annotations

import json
import shutil
from pathlib import Path


def initialize_workspace(root: Path) -> None:
    root = root.resolve()
    if not (root / "schemas" / "project.schema.json").is_file():
        raise FileNotFoundError("Run neoctl init from the Neo repository root")
    config = root / "config" / "app.json"
    if not config.exists():
        config.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / "config" / "app.example.json", config)
    (root / "data" / "projects").mkdir(parents=True, exist_ok=True)
    (root / "data" / "days").mkdir(parents=True, exist_ok=True)
    (root / "data" / "indexes").mkdir(parents=True, exist_ok=True)
    (root / ".neo" / "transactions").mkdir(parents=True, exist_ok=True)
    seeds = {
        "current.json": {"schema_version": 1, "generated_at": None, "current_day": None, "current_work_session": None},
        "projects.json": {"schema_version": 1, "generated_at": None, "projects": []},
        "calendar.json": {
            "schema_version": 1, "generated_at": None,
            "source": {"status": "not_configured", "fetched_at": None, "range_start": None, "range_end": None, "error": None},
            "events": {},
        },
    }
    for name, payload in seeds.items():
        path = root / "data" / "indexes" / name
        if not path.exists():
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
