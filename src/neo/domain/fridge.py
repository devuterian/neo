from __future__ import annotations

from ..errors import ValidationError
from ..utils import new_uuid, now_iso

CATEGORIES = {"meal", "ingredient", "snack", "drink", "dairy", "fruit", "vegetable", "meat", "seafood", "grain", "frozen", "sauce", "other"}
LOCATIONS = {"fridge", "freezer", "pantry", "shelf", "counter", "transit"}


def create_fridge() -> dict:
    return {"schema_version": 1, "items": [], "updated_at": now_iso()}


def add_item(
    fridge: dict,
    name: str,
    *,
    category: str = "other",
    quantity: float | str | None = None,
    location: str = "pantry",
    expires_at: str | None = None,
    notes: str = "",
    added_by: str = "owner",
    source: str = "",
    ordered_at: str | None = None,
    expected_at: str | None = None,
) -> dict:
    if category not in CATEGORIES:
        raise ValidationError(f"Invalid category: {category}. Choose from: {', '.join(sorted(CATEGORIES))}")
    if location not in LOCATIONS:
        raise ValidationError(f"Invalid location: {location}. Choose from: {', '.join(sorted(LOCATIONS))}")

    result = {**fridge}
    result["items"] = [dict(item) for item in fridge["items"]]
    result["items"].append({
        "item_id": new_uuid(),
        "name": name.strip(),
        "category": category,
        "quantity": quantity,
        "location": location,
        "added_at": now_iso(),
        "expires_at": expires_at,
        "consumed_at": None,
        "consumed_quantity": None,
        "notes": notes.strip(),
        "added_by": added_by,
        "source": source,
        "ordered_at": ordered_at,
        "expected_at": expected_at,
    })
    result["updated_at"] = now_iso()
    return result


def consume_item(
    fridge: dict,
    item_id: str,
    *,
    quantity: float | str | None = None,
) -> dict:
    result = {**fridge}
    result["items"] = [dict(item) for item in fridge["items"]]
    target = next((item for item in result["items"] if item["item_id"] == item_id), None)
    if target is None:
        raise ValidationError(f"Item not found: {item_id}")
    if target["consumed_at"] is not None:
        raise ValidationError(f"Item already consumed: {target['name']} (consumed at {target['consumed_at']})")
    target["consumed_at"] = now_iso()
    target["consumed_quantity"] = quantity
    result["updated_at"] = now_iso()
    return result


def remove_item(fridge: dict, item_id: str) -> dict:
    result = {**fridge}
    result["items"] = [dict(item) for item in fridge["items"]]
    target = next((item for item in result["items"] if item["item_id"] == item_id), None)
    if target is None:
        raise ValidationError(f"Item not found: {item_id}")
    result["items"].remove(target)
    result["updated_at"] = now_iso()
    return result


def arrive_item(fridge: dict, item_id: str, *, location: str = "freezer") -> dict:
    result = {**fridge}
    result["items"] = [dict(item) for item in fridge["items"]]
    target = next((item for item in result["items"] if item["item_id"] == item_id), None)
    if target is None:
        raise ValidationError(f"Item not found: {item_id}")
    if target["location"] != "transit":
        raise ValidationError(f"Item is not in transit: {target['name']} (currently at {target['location']})")
    target["location"] = location
    target["added_at"] = now_iso()
    result["updated_at"] = now_iso()
    return result


def arrive_all_transit(fridge: dict, *, location: str = "freezer") -> dict:
    result = {**fridge}
    result["items"] = [dict(item) for item in fridge["items"]]
    changed = 0
    for item in result["items"]:
        if item["location"] == "transit" and item["consumed_at"] is None:
            item["location"] = location
            item["added_at"] = now_iso()
            changed += 1
    if changed == 0:
        raise ValidationError("No items in transit")
    result["updated_at"] = now_iso()
    return result


def list_available(fridge: dict, *, location: str | None = None, category: str | None = None) -> list[dict]:
    items = [item for item in fridge["items"] if item["consumed_at"] is None]
    if location:
        items = [item for item in items if item["location"] == location]
    if category:
        items = [item for item in items if item["category"] == category]
    return items


def list_in_transit(fridge: dict) -> list[dict]:
    return [item for item in fridge["items"] if item["location"] == "transit" and item["consumed_at"] is None]


def list_all(fridge: dict) -> list[dict]:
    return fridge["items"]
