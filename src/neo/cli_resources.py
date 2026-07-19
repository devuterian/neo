from __future__ import annotations

import argparse
from typing import Any

from .mutations import MutationService, resource_names


def handle_resource(paths, args: argparse.Namespace) -> Any:
    service = MutationService(paths)
    if args.resource_command == "capabilities":
        return service.capabilities(getattr(args, "resource", None), owner_group=False)
    if args.resource_command == "get":
        return service.get(args.resource, args.target)
    if args.resource_command == "list":
        return service.list(args.resource)
    typed = {
        key: getattr(args, key)
        for key in (
            "title", "description", "slug", "wake_at", "last_date",
            "cycle_days", "days_since", "name", "category", "quantity",
            "location", "expires_at", "notes", "source", "ordered_at",
            "expected_at", "carried_from_day_id",
        )
        if hasattr(args, key) and getattr(args, key) is not None
    }
    return service.mutate(
        args.resource_command,
        args.resource,
        getattr(args, "target", None),
        field=getattr(args, "field", None),
        value=getattr(args, "value", None),
        reason=getattr(args, "reason", None),
        confirm=getattr(args, "confirm", False),
        expected_revision=getattr(args, "expected_revision", None),
        typed=typed,
    )


__all__ = ["handle_resource", "resource_names"]
