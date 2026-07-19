from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable


class MutationAction(StrEnum):
    ADD = "add"
    UPDATE = "update"
    CORRECT = "correct"
    DELETE = "delete"


@dataclass(frozen=True, slots=True)
class ResourceMutationSpec:
    name: str
    schema_name: str
    kind: str
    actions: frozenset[MutationAction]
    read_actions: frozenset[str] = frozenset({"get", "list"})
    immutable_fields: frozenset[str] = frozenset()
    owner_group_allowed: bool = False
    redacted_fields: frozenset[str] = frozenset()
    get_handler: Callable[..., Any] | None = None
    list_handler: Callable[..., Any] | None = None
    add_handler: Callable[..., Any] | None = None
    update_handler: Callable[..., Any] | None = None
    correct_handler: Callable[..., Any] | None = None
    delete_handler: Callable[..., Any] | None = None
