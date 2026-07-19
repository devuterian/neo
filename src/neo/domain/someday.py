from __future__ import annotations

from . import action_items


def create_someday() -> dict:
    return action_items.create_store()


def add_someday_item(document: dict, title: str, description: str = "") -> dict:
    return action_items.add_item(document, title, description, id_key="someday_id")


def set_someday_done(document: dict, item_id: str, done: bool) -> dict:
    return action_items.set_done(document, item_id, done, id_key="someday_id", entity_label="Someday")


def remove_someday_item(document: dict, item_id: str) -> dict:
    return action_items.remove_item(document, item_id, id_key="someday_id", entity_label="Someday")
