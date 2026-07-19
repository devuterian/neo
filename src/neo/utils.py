from __future__ import annotations

import re
import unicodedata
import uuid
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .errors import ValidationError

SEOUL = ZoneInfo("Asia/Seoul")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


MEDICATION_NS = uuid.UUID("b6c3a6d2-7a4e-5f8c-9d1b-3e2f4a5c6d7e")

def new_uuid() -> str:
    return str(uuid.uuid4())

def new_uuid5(name: str) -> str:
    return str(uuid.uuid5(MEDICATION_NS, name))



def now_seoul() -> datetime:
    return datetime.now(SEOUL)


def today_seoul() -> date:
    return now_seoul().date()


def now_iso() -> str:
    return now_seoul().isoformat(timespec="seconds")


def parse_datetime(value: str | None) -> datetime:
    if value is None:
        return now_seoul()
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValidationError(f"Invalid ISO datetime: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=SEOUL)
    return parsed.astimezone(SEOUL)


def ensure_slug(value: str) -> str:
    value = value.strip().lower()
    if not SLUG_RE.fullmatch(value):
        raise ValidationError(
            "Slug must use lowercase ASCII letters, numbers, and single hyphens."
        )
    return value


def slugify_ascii(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    if not slug:
        raise ValidationError(
            "This title cannot be converted to an English slug. Supply --slug explicitly."
        )
    return ensure_slug(slug)


def relative_posix(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()
