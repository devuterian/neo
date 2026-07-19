from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

JsonDocument = dict[str, Any]


@dataclass(slots=True)
class WorkspaceChangeSet:
    """Canonical in-memory description of one workspace transaction.

    The public ``commit_workspace`` function keeps its existing keyword
    arguments and converts them into this object before validation, derived
    output generation, and persistence.
    """

    project_updates: dict[Path, JsonDocument] = field(default_factory=dict)
    day_updates: dict[Path, JsonDocument] = field(default_factory=dict)
    calendar_update: JsonDocument | None = None
    config_update: JsonDocument | None = None
    medical_update: JsonDocument | None = None
    pending_update: JsonDocument | None = None
    someday_update: JsonDocument | None = None
    fridge_update: JsonDocument | None = None
    delete_paths: set[Path] = field(default_factory=set)

    @classmethod
    def from_updates(
        cls,
        *,
        project_updates: dict[Path, JsonDocument] | None = None,
        day_updates: dict[Path, JsonDocument] | None = None,
        calendar_update: JsonDocument | None = None,
        config_update: JsonDocument | None = None,
        medical_update: JsonDocument | None = None,
        pending_update: JsonDocument | None = None,
        someday_update: JsonDocument | None = None,
        fridge_update: JsonDocument | None = None,
        delete_paths: set[Path] | None = None,
    ) -> WorkspaceChangeSet:
        return cls(
            project_updates=dict(project_updates or {}),
            day_updates=dict(day_updates or {}),
            calendar_update=calendar_update,
            config_update=config_update,
            medical_update=medical_update,
            pending_update=pending_update,
            someday_update=someday_update,
            fridge_update=fridge_update,
            delete_paths=set(delete_paths or set()),
        )
