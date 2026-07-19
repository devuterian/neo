from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import NotFoundError


@dataclass(frozen=True)
class NeoPaths:
    root: Path

    @classmethod
    def discover(cls, start: Path | None = None) -> "NeoPaths":
        current = (start or Path.cwd()).resolve()
        for candidate in (current, *current.parents):
            if (candidate / "config" / "app.json").is_file() and (
                candidate / "schemas" / "project.schema.json"
            ).is_file():
                return cls(candidate)
        raise NotFoundError(
            "Neo workspace not found. Run 'neoctl init' from the repository root first."
        )

    @property
    def config(self) -> Path:
        return self.root / "config" / "app.json"

    @property
    def projects(self) -> Path:
        return self.root / "data" / "projects"

    @property
    def days(self) -> Path:
        return self.root / "data" / "days"

    @property
    def indexes(self) -> Path:
        return self.root / "data" / "indexes"

    @property
    def current_index(self) -> Path:
        return self.indexes / "current.json"

    @property
    def project_index(self) -> Path:
        return self.indexes / "projects.json"

    @property
    def calendar_index(self) -> Path:
        return self.indexes / "calendar.json"

    @property
    def medical_file(self) -> Path:
        return self.root / "data" / "medical.json"

    @property
    def pending_file(self) -> Path:
        return self.root / "data" / "pending.json"

    @property
    def someday_file(self) -> Path:
        return self.root / "data" / "someday.json"

    @property
    def fridge_file(self) -> Path:
        return self.root / "data" / "fridge.json"

    @property
    def private_spark(self) -> Path:
        return self.root / "data" / "private" / "spark"

    @property
    def schemas(self) -> Path:
        return self.root / "schemas"

    @property
    def brief(self) -> Path:
        return self.root / "brief.md"

    @property
    def internal(self) -> Path:
        return self.root / ".neo"

    @property
    def lock_file(self) -> Path:
        return self.internal / "lock"

    @property
    def transactions(self) -> Path:
        return self.internal / "transactions"

    @property
    def runtime(self) -> Path:
        return self.internal / "runtime"

    @property
    def last_push(self) -> Path:
        return self.runtime / "last-push.json"

    @property
    def audit_dir(self) -> Path:
        return self.root / "data" / "audit"
