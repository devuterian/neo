from __future__ import annotations

from pathlib import Path

from .models import MutationAction, ResourceMutationSpec


SCHEMA_CLASSIFICATIONS: dict[str, str] = {
    "app.schema.json": "authoritative",
    "day.schema.json": "authoritative",
    "project.schema.json": "authoritative",
    "pending.schema.json": "authoritative",
    "someday.schema.json": "authoritative",
    "fridge.schema.json": "authoritative",
    "medical.schema.json": "authoritative",
    "calendar-index.schema.json": "derived",
    "current-index.schema.json": "derived",
    "project-index.schema.json": "derived",
    "action-item.schema.json": "embedded",
    "private-spark.schema.json": "private",
}

_AUTHORITATIVE = frozenset(MutationAction)
_READ_ONLY = frozenset()
RESOURCE_SPECS: tuple[ResourceMutationSpec, ...] = (
    ResourceMutationSpec(
        "app", "app.schema.json", "authoritative",
        frozenset({MutationAction.UPDATE, MutationAction.CORRECT, MutationAction.DELETE}),
        immutable_fields=frozenset({"schema_version", "timezone"}),
        owner_group_allowed=True,
    ),
    ResourceMutationSpec(
        "day", "day.schema.json", "authoritative", _AUTHORITATIVE,
        immutable_fields=frozenset({"schema_version", "day_id", "date", "created_at"}),
        owner_group_allowed=True,
    ),
    ResourceMutationSpec(
        "project", "project.schema.json", "authoritative", _AUTHORITATIVE,
        immutable_fields=frozenset({"schema_version", "project_id", "slug", "created_at"}),
        owner_group_allowed=True,
    ),
    ResourceMutationSpec(
        "pending", "pending.schema.json", "authoritative", _AUTHORITATIVE,
        immutable_fields=frozenset({"schema_version", "pending_id", "created_at"}),
        owner_group_allowed=True,
    ),
    ResourceMutationSpec(
        "someday", "someday.schema.json", "authoritative", _AUTHORITATIVE,
        immutable_fields=frozenset({"schema_version", "someday_id", "created_at"}),
        owner_group_allowed=True,
    ),
    ResourceMutationSpec(
        "fridge", "fridge.schema.json", "authoritative", _AUTHORITATIVE,
        immutable_fields=frozenset({"schema_version", "item_id", "added_at"}),
        owner_group_allowed=True,
    ),
    ResourceMutationSpec(
        "medical", "medical.schema.json", "authoritative", _READ_ONLY,
        owner_group_allowed=False,
    ),
    ResourceMutationSpec(
        "calendar-index", "calendar-index.schema.json", "derived", _READ_ONLY,
        owner_group_allowed=False,
    ),
    ResourceMutationSpec(
        "current-index", "current-index.schema.json", "derived", _READ_ONLY,
        owner_group_allowed=False,
    ),
    ResourceMutationSpec(
        "project-index", "project-index.schema.json", "derived", _READ_ONLY,
        owner_group_allowed=False,
    ),
    ResourceMutationSpec(
        "action-item", "action-item.schema.json", "embedded", _READ_ONLY,
        owner_group_allowed=False,
    ),
    ResourceMutationSpec(
        "private-spark", "private-spark.schema.json", "private", _READ_ONLY,
        owner_group_allowed=False,
        redacted_fields=frozenset({"note", "partner", "mood", "condition", "discomfort"}),
    ),
)

_BY_NAME = {spec.name: spec for spec in RESOURCE_SPECS}


def resource_names() -> tuple[str, ...]:
    return tuple(spec.name for spec in RESOURCE_SPECS)


def get_resource(name: str) -> ResourceMutationSpec:
    try:
        return _BY_NAME[name]
    except KeyError as exc:
        raise ValueError(f"Unknown resource: {name}") from exc


def schema_coverage(schema_dir: Path) -> dict[str, str]:
    actual = {path.name for path in schema_dir.glob("*.schema.json")}
    expected = set(SCHEMA_CLASSIFICATIONS)
    missing = sorted(actual - expected)
    stale = sorted(expected - actual)
    if missing or stale:
        details = []
        if missing:
            details.append(f"unclassified schemas: {', '.join(missing)}")
        if stale:
            details.append(f"missing schema files: {', '.join(stale)}")
        raise ValueError("; ".join(details))
    return dict(SCHEMA_CLASSIFICATIONS)


def capabilities(*, owner_group: bool = False) -> list[dict[str, object]]:
    result = []
    for spec in RESOURCE_SPECS:
        actions = sorted(action.value for action in spec.actions)
        if owner_group:
            actions = actions if spec.owner_group_allowed else []
        result.append({
            "resource": spec.name,
            "schema": spec.schema_name,
            "kind": spec.kind,
            "actions": actions,
            "read_actions": sorted(spec.read_actions),
            "owner_group_allowed": spec.owner_group_allowed,
        })
    return result
