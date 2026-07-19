from __future__ import annotations

from pathlib import Path
from typing import Any

from .git_sync import _git_commit
from .paths import NeoPaths
from .repository import Repository
from .transaction import read_json, repository_lock, write_batch
from .validation import validate_document
from .workspace_changes import WorkspaceChangeSet
from .workspace_derived import (
    add_json_if_changed,
    build_derived_workspace,
    read_optional_json,
    text_file_changed,
)
from .workspace_validation import validate_cross_references

JsonDocument = dict[str, Any]


def load_documents(
    paths: NeoPaths,
) -> tuple[dict[Path, JsonDocument], dict[Path, JsonDocument]]:
    repo = Repository(paths)
    projects = {location.path: location.data for location in repo.load_projects()}
    days = {path: read_json(path) for path in repo.day_files()}
    return projects, days


def commit_workspace(
    paths: NeoPaths,
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
) -> None:
    """Validate and persist one workspace transaction.

    The legacy keyword interface remains stable. Internally the updates are
    normalized into a ``WorkspaceChangeSet`` before any repository state is
    read or written.
    """

    changes = WorkspaceChangeSet.from_updates(
        project_updates=project_updates,
        day_updates=day_updates,
        calendar_update=calendar_update,
        config_update=config_update,
        medical_update=medical_update,
        pending_update=pending_update,
        someday_update=someday_update,
        fridge_update=fridge_update,
        delete_paths=delete_paths,
    )
    _commit_change_set(paths, changes)


def _commit_change_set(paths: NeoPaths, changes: WorkspaceChangeSet) -> None:
    with repository_lock(paths):
        projects, days = load_documents(paths)
        for path in changes.delete_paths:
            projects.pop(path, None)
            days.pop(path, None)
        projects.update(changes.project_updates)
        days.update(changes.day_updates)

        _validate_canonical_documents(paths, projects, days)

        calendar = (
            changes.calendar_update
            if changes.calendar_update is not None
            else read_json(paths.calendar_index)
        )
        validate_document(paths, calendar, "calendar-index.schema.json", "calendar index")

        config = (
            changes.config_update
            if changes.config_update is not None
            else read_json(paths.config)
        )
        validate_document(paths, config, "app.schema.json", "config/app.json")

        medical = (
            changes.medical_update
            if changes.medical_update is not None
            else read_optional_json(paths.medical_file)
        )
        if medical is not None:
            validate_document(paths, medical, "medical.schema.json", "data/medical.json")

        pending = (
            changes.pending_update
            if changes.pending_update is not None
            else read_optional_json(paths.pending_file)
        )
        if pending is not None:
            validate_document(paths, pending, "pending.schema.json", "data/pending.json")

        someday = (
            changes.someday_update
            if changes.someday_update is not None
            else read_optional_json(paths.someday_file)
        )
        if someday is not None:
            validate_document(paths, someday, "someday.schema.json", "data/someday.json")
        validate_cross_references(
            projects,
            days,
            pending=pending,
            someday=someday,
        )

        fridge = (
            changes.fridge_update
            if changes.fridge_update is not None
            else read_optional_json(paths.fridge_file)
        )
        if fridge is not None:
            validate_document(paths, fridge, "fridge.schema.json", "data/fridge.json")

        derived = build_derived_workspace(
            paths,
            projects,
            days,
            calendar=calendar,
            medical=medical,
            pending=pending,
        )
        validate_document(
            paths,
            derived.current_index,
            "current-index.schema.json",
            "current index",
        )
        validate_document(
            paths,
            derived.project_index,
            "project-index.schema.json",
            "project index",
        )

        json_files: dict[Path, Any] = {
            **changes.project_updates,
            **changes.day_updates,
        }
        add_json_if_changed(
            json_files,
            paths.current_index,
            derived.current_index,
            timestamp_field="generated_at",
        )
        add_json_if_changed(
            json_files,
            paths.project_index,
            derived.project_index,
            timestamp_field="generated_at",
        )

        if changes.calendar_update is not None:
            add_json_if_changed(
                json_files,
                paths.calendar_index,
                changes.calendar_update,
                timestamp_fields=[
                    "generated_at",
                    ("source", "fetched_at"),
                    ("source", "range_start"),
                    ("source", "range_end"),
                ],
            )
        if changes.config_update is not None:
            add_json_if_changed(json_files, paths.config, changes.config_update)
        if changes.medical_update is not None:
            add_json_if_changed(json_files, paths.medical_file, changes.medical_update)
        if changes.pending_update is not None:
            add_json_if_changed(json_files, paths.pending_file, changes.pending_update)
        if changes.someday_update is not None:
            add_json_if_changed(json_files, paths.someday_file, changes.someday_update)
        if changes.fridge_update is not None:
            add_json_if_changed(json_files, paths.fridge_file, changes.fridge_update)

        text_files: dict[Path, str] = {}
        # Someday is intentionally not an input to derived views. Keep the
        # transaction from materializing or refreshing brief.md for a
        # someday-only change, including in a synthetic repository.
        someday_only = changes.someday_update is not None and not any(
            (
                changes.project_updates,
                changes.day_updates,
                changes.calendar_update is not None,
                changes.config_update is not None,
                changes.medical_update is not None,
                changes.pending_update is not None,
                changes.fridge_update is not None,
                changes.delete_paths,
            )
        )
        if not someday_only and text_file_changed(paths.brief, derived.brief):
            text_files[paths.brief] = derived.brief

        if not json_files and not text_files and not changes.delete_paths:
            return

        write_batch(
            paths,
            json_files,
            text_files,
            delete_paths=changes.delete_paths,
        )
        _git_commit(
            paths,
            list(json_files) + list(text_files),
            changes.delete_paths,
        )


def rebuild_derived(paths: NeoPaths) -> None:
    with repository_lock(paths):
        projects, days = load_documents(paths)
        validate_cross_references(projects, days)
        calendar = read_json(paths.calendar_index)
        derived = build_derived_workspace(
            paths,
            projects,
            days,
            calendar=calendar,
            medical=read_optional_json(paths.medical_file),
            pending=read_optional_json(paths.pending_file),
        )
        write_batch(
            paths,
            {
                paths.current_index: derived.current_index,
                paths.project_index: derived.project_index,
            },
            {paths.brief: derived.brief},
        )


def _validate_canonical_documents(
    paths: NeoPaths,
    projects: dict[Path, JsonDocument],
    days: dict[Path, JsonDocument],
) -> None:
    for path, project in projects.items():
        validate_document(paths, project, "project.schema.json", str(path))
    for path, day in days.items():
        validate_document(paths, day, "day.schema.json", str(path))
    validate_cross_references(projects, days)


# Compatibility alias for existing internal imports and tests.
_validate_cross_references = validate_cross_references
