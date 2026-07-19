from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .errors import ConflictError, NotFoundError
from .paths import NeoPaths
from .repository_catalog import (
    JsonDocument,
    ProjectLocation,
    RepositoryCatalog,
    TaskLocation,
    resolve_milestone,
)
from .transaction import read_json


class Repository:
    def __init__(self, paths: NeoPaths):
        self.paths = paths

    def project_files(self) -> Iterable[Path]:
        return sorted(self.paths.projects.glob("*.json"))

    def day_files(self) -> Iterable[Path]:
        return sorted(self.paths.days.glob("*/*.json"))

    def load_projects(self) -> list[ProjectLocation]:
        return [
            ProjectLocation(path, read_json(path))
            for path in self.project_files()
        ]

    def load_catalog(self) -> RepositoryCatalog:
        """Build one immutable lookup projection from the current project files."""

        return RepositoryCatalog.from_locations(self.load_projects())

    def resolve_project(self, token: str) -> ProjectLocation:
        return self.load_catalog().resolve_project(token)

    def resolve_milestone(
        self,
        project: JsonDocument,
        token: str,
    ) -> JsonDocument:
        return resolve_milestone(project, token)

    def resolve_task(
        self,
        token: str,
        project_token: str | None = None,
    ) -> TaskLocation:
        return self.load_catalog().resolve_task(token, project_token)

    def project_path_for_slug(self, slug: str) -> Path:
        return self.paths.projects / f"{slug}.json"

    def day_path(self, date_value: str) -> Path:
        return self.paths.days / date_value[:4] / f"{date_value}.json"

    def current_day_location(self) -> tuple[Path, JsonDocument]:
        current = read_json(self.paths.current_index)
        entry = current.get("current_day")
        if not entry:
            raise NotFoundError("No active life day")
        path = self.paths.root / entry["path"]
        if not path.is_file():
            raise NotFoundError("Current life-day index points to a missing file")
        return path, read_json(path)

    def day_location_by_date(self, date_str: str) -> tuple[Path, JsonDocument]:
        path = self.day_path(date_str)
        if not path.is_file():
            raise NotFoundError(f"No life day found for date: {date_str}")
        return path, read_json(path)

    def open_session(
        self,
    ) -> tuple[Path, JsonDocument, JsonDocument]:
        day_path, day = self.current_day_location()
        sessions = [
            session
            for session in day["work_sessions"]
            if session["checked_out_at"] is None
        ]
        if not sessions:
            raise NotFoundError("No open work session")
        if len(sessions) > 1:
            raise ConflictError("More than one open work session exists")
        return day_path, day, sessions[0]
