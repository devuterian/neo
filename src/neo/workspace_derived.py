from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .indexes import build_indexes_from_documents
from .paths import NeoPaths
from .renderer import render_brief
from .transaction import read_json

JsonDocument = dict[str, Any]


@dataclass(frozen=True, slots=True)
class DerivedWorkspace:
    current_index: JsonDocument
    project_index: JsonDocument
    brief: str


def read_optional_json(path: Path) -> JsonDocument | None:
    if path.is_file():
        return read_json(path)
    return None


def build_derived_workspace(
    paths: NeoPaths,
    projects: Mapping[Path, JsonDocument],
    days: Mapping[Path, JsonDocument],
    *,
    calendar: JsonDocument,
    medical: JsonDocument | None,
    pending: JsonDocument | None,
) -> DerivedWorkspace:
    current_index, project_index = build_indexes_from_documents(
        paths,
        projects.items(),
        days.items(),
    )
    brief = render_brief(
        project_docs=projects.items(),
        day_docs=days.items(),
        calendar_index=calendar,
        medical=medical or {},
        pending=pending or {},
    )
    return DerivedWorkspace(
        current_index=current_index,
        project_index=project_index,
        brief=brief,
    )


def add_json_if_changed(
    target: dict[Path, Any],
    file_path: Path,
    content: JsonDocument,
    *,
    timestamp_field: str | None = None,
    timestamp_fields: list[str | tuple[str, ...]] | None = None,
) -> None:
    """Add a JSON write only when semantic content changed."""

    if _files_are_equal(file_path, content):
        return

    ignored_fields = timestamp_fields or ([timestamp_field] if timestamp_field else None)
    if ignored_fields is None or not file_path.is_file():
        target[file_path] = content
        return

    try:
        existing = read_json(file_path)
    except (json.JSONDecodeError, OSError):
        target[file_path] = content
        return

    existing_copy = _deep_copy(existing)
    content_copy = _deep_copy(content)
    for key in ignored_fields:
        if isinstance(key, str):
            existing_copy.pop(key, None)
            content_copy.pop(key, None)
        else:
            _pop_nested(existing_copy, key)
            _pop_nested(content_copy, key)

    if existing_copy != content_copy:
        target[file_path] = content


def text_file_changed(path: Path, text: str) -> bool:
    if not path.is_file():
        return True
    return _normalize_text(path.read_text(encoding="utf-8")) != _normalize_text(text)


def _files_are_equal(path: Path, new_content: JsonDocument) -> bool:
    if not path.is_file():
        return False
    try:
        existing = read_json(path)
    except (json.JSONDecodeError, OSError):
        return False
    return existing == new_content


def _normalize_text(text: str) -> str:
    """Ignore generated timestamps when comparing reproducible brief output."""

    text = re.sub(
        r"^- Generated: `[^`]+`$",
        "- Generated: `__STRIPPED__`",
        text,
        flags=re.MULTILINE,
    )
    return re.sub(
        r"^- 마지막 조회: `[^`]+`$",
        "- 마지막 조회: `__STRIPPED__`",
        text,
        flags=re.MULTILINE,
    )


def _deep_copy(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _deep_copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_deep_copy(item) for item in value]
    return value


def _pop_nested(document: dict[str, Any], keys: tuple[str, ...]) -> None:
    current: Any = document
    for key in keys[:-1]:
        if not isinstance(current, dict):
            return
        current = current.get(key)
    if isinstance(current, dict):
        current.pop(keys[-1], None)
