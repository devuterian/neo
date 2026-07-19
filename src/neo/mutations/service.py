from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from ..domain import days as day_domain
from ..domain import fridge as fridge_domain
from ..domain import medical as medical_domain
from ..domain import pending as pending_domain
from ..domain import projects as project_domain
from ..domain import someday as someday_domain
from ..errors import ConflictError, NotFoundError, ValidationError
from ..paths import NeoPaths
from ..repository import Repository
from ..transaction import read_json
from ..utils import new_uuid, now_iso, parse_datetime
from ..validation import validate_document
from ..workspace import commit_workspace
from .models import MutationAction
from ..audit import record_correction
from .registry import capabilities, get_resource, schema_coverage

Json = dict[str, Any]

_FIELD_MAP: dict[str, frozenset[str]] = {
    "app": frozenset({"auto_wake", "brief.path", "calendar.managed_calendar_id",
                      "calendar.tomato_color_id", "notifications.status_check",
                      "notifications.work_start_check", "notifications.work_end_check"}),
    "day": frozenset({"wake_at", "sleep_at", "status", "workday_capacity"}),
    "project": frozenset({"title", "slug", "description", "status"}),
    "pending": frozenset({"title", "description", "done", "carried_from_day_id"}),
    "someday": frozenset({"title", "description", "done"}),
    "fridge": frozenset({"name", "category", "quantity", "location", "expires_at",
                         "notes", "source", "ordered_at", "expected_at"}),
    "medical": frozenset({"last_date", "cycle_days", "days_since", "note"}),
}


class MutationService:
    def __init__(self, paths: NeoPaths):
        self.paths = paths

    def capabilities(self, resource: str | None = None, *, owner_group: bool = False) -> dict[str, Any]:
        resources = capabilities(owner_group=owner_group)
        if resource is not None:
            get_resource(resource)
            resources = [item for item in resources if item["resource"] == resource]
        return {
            "success": True,
            "schema_classifications": schema_coverage(self.paths.schemas),
            "resources": resources,
        }

    def get(self, resource: str, target: str | None = None) -> dict[str, Any]:
        spec = get_resource(resource)
        if spec.kind == "private":
            raise ValidationError("Private resource is not available through this interface")
        path, document, selected = self._resolve(spec.name, target)
        if selected is not None:
            return copy.deepcopy(selected)
        if spec.name in {"current-index", "project-index", "calendar-index"}:
            return copy.deepcopy(document)
        return copy.deepcopy(document)

    def list(self, resource: str) -> dict[str, Any]:
        spec = get_resource(resource)
        if spec.kind == "private":
            raise ValidationError("Private resource is not available through this interface")
        path, document, _ = self._resolve(spec.name, None)
        if spec.name in {"pending", "someday"}:
            return {"items": copy.deepcopy(document.get("items", [])),
                    "count": len(document.get("items", []))}
        if spec.name == "fridge":
            return {"items": copy.deepcopy(document.get("items", [])),
                    "count": len(document.get("items", []))}
        if spec.name == "project":
            items = []
            for project_path in sorted(self.paths.projects.glob("*.json")):
                project = read_json(project_path)
                items.append({
                    "project_id": project["project_id"],
                    "title": project["title"],
                    "slug": project["slug"],
                    "status": project["status"],
                })
            return {"items": items, "count": len(items)}
        if spec.name == "day":
            items = []
            for day_path in sorted(self.paths.days.glob("*/*.json")):
                day = read_json(day_path)
                items.append({
                    "day_id": day["day_id"],
                    "date": day["date"],
                    "status": day["status"],
                })
            return {"items": items, "count": len(items)}
        return {"items": [copy.deepcopy(document)], "count": 1} if path else {"items": [], "count": 0}

    def mutate(
        self,
        action: str,
        resource: str,
        target: str | None = None,
        *,
        field: str | None = None,
        value: Any = None,
        reason: str | None = None,
        confirm: bool = False,
        expected_revision: str | None = None,
        typed: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        spec = get_resource(resource)
        try:
            mutation = __import__("neo.mutations.models", fromlist=["MutationAction"]).MutationAction(action)
        except ValueError as exc:
            raise ValidationError(f"Unsupported mutation action: {action}") from exc
        if spec.kind != "authoritative" or mutation not in spec.actions:
            raise ValidationError(f"Resource {resource} does not support {action}")
        typed = dict(typed or {})
        if mutation is MutationAction.DELETE:
            if not confirm:
                raise ValidationError("delete requires --confirm")
            if not (reason and reason.strip()):
                raise ValidationError("delete requires --reason")
        if mutation is MutationAction.CORRECT and not (reason and reason.strip()):
            raise ValidationError("correct requires --reason")

        path, current, selected = self._resolve(resource, target)
        if mutation is MutationAction.ADD:
            if current is not None and resource in {"day", "project"} and path is not None:
                pass
            before = None
            updated, write_target, deletes, result_target = self._add(resource, typed)
        else:
            if current is None:
                raise NotFoundError(f"No {resource} record found")
            if expected_revision and expected_revision != revision(current):
                raise ConflictError("Resource revision conflict")
            before_doc = copy.deepcopy(current)
            updated, write_target, deletes, result_target = self._change(
                resource, mutation.value, target, current, selected,
                field=field, value=value, reason=reason,
            )
            before = self._summary(resource, selected or current, field)
            if mutation is MutationAction.DELETE and resource not in {"app", "pending", "someday", "fridge"}:
                updated = None
            before_revision = revision(before_doc)
            after_revision = revision(updated) if updated is not None else None
        if mutation is MutationAction.ADD:
            before_revision = None
            after_revision = revision(updated)
            before = None
        self._commit(resource, write_target, updated, deletes)
        after = self._summary(resource, self._selected_after(resource, updated, result_target), field)
        changed_fields = self._changed_fields(before, after)
        # Record correction audit after successful commit
        if mutation is MutationAction.CORRECT and reason:
            record_correction(
                self.paths,
                resource=resource,
                target=str(result_target),
                changed_fields=changed_fields,
                before=before,
                after=after,
                reason=reason.strip(),
            )
        return {
            "success": True,
            "action": action,
            "resource": resource,
            "target": result_target,
            "subject": "owner",
            "revision_before": before_revision,
            "revision_after": after_revision,
            "changed_fields": changed_fields,
            "before": before,
            "after": after,
            **({"reason": reason.strip()} if mutation is MutationAction.CORRECT else {}),
        }

    def _resolve(self, resource: str, target: str | None) -> tuple[Path | None, Json | None, Json | None]:
        if resource == "app":
            document = read_json(self.paths.config)
            return self.paths.config, document, None
        if resource == "project":
            locations = Repository(self.paths).load_projects()
            if target is None:
                return None, None, None
            location = Repository(self.paths).resolve_project(target)
            return location.path, location.data, None
        if resource == "day":
            if target is None:
                return None, None, None
            repo = Repository(self.paths)
            try:
                path, document = repo.day_location_by_date(target)
            except NotFoundError:
                for candidate in repo.day_files():
                    item = read_json(candidate)
                    if item.get("day_id") == target:
                        return candidate, item, None
                raise
            return path, document, None
        if resource in {"pending", "someday", "fridge", "medical"}:
            path = {
                "pending": self.paths.pending_file,
                "someday": self.paths.someday_file,
                "fridge": self.paths.fridge_file,
                "medical": self.paths.medical_file,
            }[resource]
            if not path.is_file():
                if target is None and resource in {"pending", "someday", "fridge"}:
                    factory = {"pending": pending_domain.create_pending,
                               "someday": someday_domain.create_someday,
                               "fridge": fridge_domain.create_fridge}[resource]
                    return path, factory(), None
                return path, None, None
            document = read_json(path)
            if target is None:
                return path, document, None
            key = {"pending": "pending_id", "someday": "someday_id",
                   "fridge": "item_id"}.get(resource)
            if key:
                selected = next((item for item in document.get("items", []) if item.get(key) == target), None)
                if selected is None:
                    raise NotFoundError(f"{resource} target not found: {target}")
                return path, document, selected
            return path, document, None
        if resource in {"current-index", "project-index", "calendar-index"}:
            path = {
                "current-index": self.paths.current_index,
                "project-index": self.paths.project_index,
                "calendar-index": self.paths.calendar_index,
            }[resource]
            return path, read_json(path), None
        if resource in {"action-item", "private-spark"}:
            raise ValidationError(f"{resource} is not an independent resource")
        raise ValidationError(f"Unknown resource: {resource}")

    def _add(self, resource: str, typed: dict[str, Any]) -> tuple[Json, Path | None, set[Path], str]:
        if resource == "day":
            wake_at = typed.get("wake_at") or typed.get("value")
            if not wake_at:
                raise ValidationError("day add requires --wake-at")
            document = day_domain.create_day(wake_at)
            path = Repository(self.paths).day_path(document["date"])
            if path.exists():
                raise ConflictError(f"Day already exists: {document['date']}")
            return document, path, set(), document["date"]
        if resource == "project":
            title = _required_text(typed.get("title"), "title")
            slug = typed.get("slug") or _slug(title)
            path = Repository(self.paths).project_path_for_slug(slug)
            if path.exists():
                raise ConflictError(f"Project slug already exists: {slug}")
            return project_domain.create_project(title, slug, typed.get("description", "")), path, set(), slug
        if resource in {"pending", "someday"}:
            title = _required_text(typed.get("title"), "title")
            path = self.paths.pending_file if resource == "pending" else self.paths.someday_file
            doc = read_json(path) if path.is_file() else (
                pending_domain.create_pending() if resource == "pending" else someday_domain.create_someday()
            )
            updated = (
                pending_domain.add_pending_item(doc, title, typed.get("description", ""), typed.get("carried_from_day_id"))
                if resource == "pending"
                else someday_domain.add_someday_item(doc, title, typed.get("description", ""))
            )
            return updated, path, set(), updated["items"][-1][{"pending": "pending_id", "someday": "someday_id"}[resource]]
        if resource == "fridge":
            name = _required_text(typed.get("name"), "name")
            path = self.paths.fridge_file
            doc = read_json(path) if path.is_file() else fridge_domain.create_fridge()
            updated = fridge_domain.add_item(doc, name, category=typed.get("category", "other"),
                quantity=typed.get("quantity"), location=typed.get("location", "pantry"),
                expires_at=typed.get("expires_at"), notes=typed.get("notes", ""),
                source=typed.get("source", ""), ordered_at=typed.get("ordered_at"),
                expected_at=typed.get("expected_at"))
            return updated, path, set(), updated["items"][-1]["item_id"]
        if resource == "medical":
            if self.paths.medical_file.exists():
                raise ConflictError("medical record already exists")
            if typed.get("last_date"):
                document = medical_domain.create_medical_v2(typed["last_date"], typed.get("cycle_days", 21), typed.get("note"))
            elif typed.get("days_since") is not None:
                document = medical_domain.create_medical(int(typed["days_since"]), typed.get("note"))
            else:
                raise ValidationError("medical add requires --days-since or --last-injection")
            return document, self.paths.medical_file, set(), "medical"
        if resource == "app":
            raise ConflictError("Application config already exists")
        raise ValidationError(f"Unsupported add resource: {resource}")

    def _change(self, resource: str, action: str, target: str | None, current: Json,
                selected: Json | None, *, field: str | None, value: Any, reason: str | None):
        if action == "delete":
            return self._delete(resource, current, selected, target)
        if field not in _FIELD_MAP.get(resource, frozenset()):
            raise ValidationError(f"Unsupported {resource} field: {field}")
        if field in get_resource(resource).immutable_fields:
            raise ValidationError(f"Field is immutable: {field}")
        if selected is None and resource in {"pending", "someday", "fridge"}:
            raise ValidationError(f"{resource} update requires a target item")
        updated = copy.deepcopy(current)
        if selected is not None:
            key = {"pending": "pending_id", "someday": "someday_id", "fridge": "item_id"}[resource]
            item = next(item for item in updated["items"] if item[key] == selected[key])
            old = item.get(field)
            item[field] = _typed_value(resource, field, value)
            updated["updated_at"] = now_iso()
        else:
            old = updated.get(field)
            _set_document_field(updated, resource, field, value)
        if resource == "day":
            _validate_day_field(updated, field)
        if resource == "medical":
            updated = _refresh_medical(updated, field)
        return updated, self._path_for(resource, current, target), set(), target or self._target_for(resource, updated)

    def _delete(self, resource: str, current: Json, selected: Json | None, target: str | None):
        if resource in {"pending", "someday", "fridge"}:
            if selected is None:
                raise ValidationError(f"{resource} delete requires a target item")
            key = {"pending": "pending_id", "someday": "someday_id", "fridge": "item_id"}[resource]
            updated = copy.deepcopy(current)
            updated["items"] = [item for item in updated["items"] if item[key] != selected[key]]
            updated["updated_at"] = now_iso()
            return updated, self._path_for(resource, current, target), set(), selected[key]
        if resource == "day":
            if current["status"] == "active":
                raise ConflictError("Cannot delete the active life day")
            self._ensure_day_not_referenced(current["day_id"])
            return current, self._path_for(resource, current, target), {self._path_for(resource, current, target)}, target
        if resource == "project":
            self._ensure_project_not_referenced(current["project_id"])
            return current, self._path_for(resource, current, target), {self._path_for(resource, current, target)}, target
        if resource == "medical":
            return current, self.paths.medical_file, {self.paths.medical_file}, "medical"
        if resource == "app":
            return _default_config(), self.paths.config, set(), "app"
        raise ValidationError(f"Unsupported delete resource: {resource}")

    def _commit(self, resource: str, path: Path | None, updated: Json | None, deletes: set[Path]):
        kwargs: dict[str, Any] = {"delete_paths": deletes}
        if updated is not None:
            key = {
                "app": "config_update", "day": "day_updates", "project": "project_updates",
                "pending": "pending_update", "someday": "someday_update",
                "fridge": "fridge_update", "medical": "medical_update",
            }.get(resource)
            if key == "day_updates":
                kwargs[key] = {path: updated}
            elif key == "project_updates":
                kwargs[key] = {path: updated}
            elif key:
                kwargs[key] = updated
        commit_workspace(self.paths, **kwargs)

    def _path_for(self, resource: str, current: Json, target: str | None) -> Path:
        if resource == "day":
            return Repository(self.paths).day_path(current["date"])
        if resource == "project":
            return Repository(self.paths).project_path_for_slug(current["slug"])
        if resource == "app":
            return self.paths.config
        if resource == "pending":
            return self.paths.pending_file
        if resource == "someday":
            return self.paths.someday_file
        if resource == "fridge":
            return self.paths.fridge_file
        if resource == "medical":
            return self.paths.medical_file
        raise ValidationError(f"Unsupported resource: {resource}")

    def _selected_after(self, resource: str, updated: Json | None, target: str | None) -> Json | None:
        if updated is None:
            return None
        key = {"pending": "pending_id", "someday": "someday_id", "fridge": "item_id"}.get(resource)
        if key and target:
            return next((item for item in updated.get("items", []) if item.get(key) == target), None)
        return updated

    def _summary(self, resource: str, value: Json | None, field: str | None) -> Json | None:
        if value is None:
            return None
        if field:
            return {field: value.get(field)}
        identifiers = {
            "day": ("day_id", "date", "status"),
            "project": ("project_id", "title", "slug", "status"),
            "pending": ("pending_id", "title", "done"),
            "someday": ("someday_id", "title", "done"),
            "fridge": ("item_id", "name", "location", "consumed_at"),
            "medical": ("schema_version", "days_since", "last_date"),
            "app": ("schema_version", "timezone"),
        }.get(resource)
        return {key: value.get(key) for key in (identifiers or value.keys()) if key in value}

    def _changed_fields(self, before: Json | None, after: Json | None) -> list[str]:
        if before is None:
            return sorted(after or {})
        if after is None:
            return sorted(before)
        return sorted({key for key in set(before) | set(after) if before.get(key) != after.get(key)})

    def _ensure_day_not_referenced(self, day_id: str) -> None:
        if self.paths.pending_file.is_file():
            pending = read_json(self.paths.pending_file)
            if any(item.get("carried_from_day_id") == day_id for item in pending.get("items", [])):
                raise ConflictError("Cannot delete a day referenced by pending items")

    def _ensure_project_not_referenced(self, project_id: str) -> None:
        for path in self.paths.days.glob("*/*.json"):
            day = read_json(path)
            if any(item.get("project_id") == project_id for item in [*day.get("work_plan", []), *day.get("work_sessions", [])]):
                raise ConflictError("Cannot delete a project referenced by a life day")

    def _target_for(self, resource: str, document: Json) -> str:
        return str(document.get({"day": "date", "project": "slug", "medical": "schema_version",
                                 "app": "schema_version"}.get(resource, "updated_at")))


def revision(document: Json | None) -> str | None:
    if document is None:
        return None
    canonical = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field} must not be empty")
    return value.strip()


def _slug(value: str) -> str:
    import re
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    if not slug:
        raise ValidationError("slug must contain ASCII letters or digits")
    return slug


def _typed_value(resource: str, field: str, value: Any) -> Any:
    if field in {"wake_at", "sleep_at", "last_date", "ordered_at", "expected_at"}:
        return str(value).strip()
    if field in {"done"}:
        if isinstance(value, bool):
            return value
        if str(value).casefold() in {"true", "1", "yes"}:
            return True
        if str(value).casefold() in {"false", "0", "no"}:
            return False
        raise ValidationError(f"{field} must be true or false")
    if field in {"workday_capacity", "quantity"}:
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{field} must be numeric") from exc
    if field in {"cycle_days", "days_since"}:
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{field} must be an integer") from exc
    return str(value).strip()


def _set_document_field(document: Json, resource: str, field: str, value: Any) -> None:
    value = _typed_value(resource, field, value)
    if "." in field:
        first, second = field.split(".", 1)
        if first not in document or not isinstance(document[first], dict):
            raise ValidationError(f"Unknown field: {field}")
        document[first][second] = value
    else:
        document[field] = value
    if resource in {"day", "project", "app"} and "updated_at" in document:
        document["updated_at"] = now_iso()


def _validate_day_field(document: Json, field: str) -> None:
    if field == "wake_at":
        wake = parse_datetime(document["wake_at"])
        if wake.date().isoformat() != document["date"]:
            raise ValidationError("wake_at date must match day date")
    if field == "sleep_at" and document.get("sleep_at"):
        if parse_datetime(document["sleep_at"]) < parse_datetime(document["wake_at"]):
            raise ValidationError("sleep_at cannot precede wake_at")


def _refresh_medical(document: Json, field: str) -> Json:
    if "last_date" in document and field in {"last_date", "cycle_days"}:
        return medical_domain.record_injection(
            document,
            document["last_date"],
            document.get("note"),
        )
    return document


def _default_config() -> Json:
    return {
        "schema_version": 1,
        "timezone": "Asia/Seoul",
        "calendar": {"managed_calendar_id": None, "read_only_calendar_ids": [], "tomato_color_id": None},
        "notifications": {"status_check": "20:00", "work_start_check": "22:50", "work_end_check": "03:00"},
        "brief": {"path": "brief.md"},
        "auto_wake": "ask",
    }
