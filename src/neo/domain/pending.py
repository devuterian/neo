from __future__ import annotations

from ..utils import now_iso
from . import action_items


def create_pending() -> dict:
    return action_items.create_store()


def add_pending_item(pending: dict, title: str, description: str = "", carried_from_day_id: str | None = None) -> dict:
    result = action_items.add_item(pending, title, description, id_key="pending_id")
    result["items"][-1]["carried_from_day_id"] = carried_from_day_id
    return result


def set_pending_done(pending: dict, pending_id: str, done: bool) -> dict:
    return action_items.set_done(pending, pending_id, done, id_key="pending_id", entity_label="Pending")


def remove_pending_item(pending: dict, pending_id: str) -> dict:
    return action_items.remove_item(pending, pending_id, id_key="pending_id", entity_label="Pending")
