from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..errors import ValidationError
from ..utils import new_uuid, now_iso


def create_store() -> dict[str, Any]:
    return {"schema_version": 1, "items": [], "updated_at": now_iso()}


def add_item(document: dict[str, Any], title: str, description: str = "", *, id_key: str) -> dict[str, Any]:
    title = title.strip()
    if not title:
        raise ValidationError("Item title must not be empty")
    result = deepcopy(document)
    result["items"] = [*document["items"], {
        id_key: new_uuid(), "title": title, "description": description.strip(),
        "done": False, "created_at": now_iso(),
    }]
    result["updated_at"] = now_iso()
    return result


def set_done(
    document: dict[str, Any],
    item_id: str,
    done: bool,
    *,
    id_key: str,
    entity_label: str = "Item",
) -> dict[str, Any]:
    result = deepcopy(document)
    target = next((item for item in result["items"] if item.get(id_key) == item_id), None)
    if target is None:
        raise ValidationError(f"{entity_label} item not found: {item_id}")
    if target["done"] == done:
        return result
    target["done"] = done
    result["updated_at"] = now_iso()
    return result


def remove_item(
    document: dict[str, Any],
    item_id: str,
    *,
    id_key: str,
    entity_label: str = "Item",
) -> dict[str, Any]:
    result = deepcopy(document)
    if not any(item.get(id_key) == item_id for item in result["items"]):
        raise ValidationError(f"{entity_label} item not found: {item_id}")
    result["items"] = [item for item in result["items"] if item.get(id_key) != item_id]
    result["updated_at"] = now_iso()
    return result
