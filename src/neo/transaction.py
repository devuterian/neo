from __future__ import annotations

import fcntl
import json
import os
import shutil
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .paths import NeoPaths


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@contextmanager
def repository_lock(paths: NeoPaths) -> Iterator[None]:
    paths.internal.mkdir(parents=True, exist_ok=True)
    paths.lock_file.touch(exist_ok=True)
    with paths.lock_file.open("r+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            recover_incomplete_transactions(paths)
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def recover_incomplete_transactions(paths: NeoPaths) -> None:
    paths.transactions.mkdir(parents=True, exist_ok=True)
    for tx_dir in paths.transactions.iterdir():
        if not tx_dir.is_dir():
            continue
        manifest_path = tx_dir / "manifest.json"
        if not manifest_path.is_file():
            shutil.rmtree(tx_dir, ignore_errors=True)
            continue
        try:
            manifest = read_json(manifest_path)
        except Exception:
            shutil.rmtree(tx_dir, ignore_errors=True)
            continue
        for entry in manifest.get("files", []):
            target = paths.root / entry["path"]
            backup = tx_dir / entry["backup"]
            if entry["existed"]:
                target.parent.mkdir(parents=True, exist_ok=True)
                if backup.exists():
                    shutil.copy2(backup, target)
            else:
                target.unlink(missing_ok=True)
        shutil.rmtree(tx_dir, ignore_errors=True)


def write_batch(
    paths: NeoPaths,
    json_files: dict[Path, Any],
    text_files: dict[Path, str] | None = None,
    delete_paths: set[Path] | None = None,
) -> None:
    text_files = text_files or {}
    delete_paths = delete_paths or set()
    paths.transactions.mkdir(parents=True, exist_ok=True)
    tx_dir = paths.transactions / str(uuid.uuid4())
    tx_dir.mkdir(parents=True)
    entries: list[dict[str, Any]] = []
    overlap = (set(json_files) | set(text_files)) & delete_paths
    if overlap:
        raise ValueError(f"Cannot write and delete the same path: {sorted(str(p) for p in overlap)}")
    ordered_targets = list(json_files) + list(text_files) + list(delete_paths)

    for index, target in enumerate(ordered_targets):
        relative = target.resolve().relative_to(paths.root.resolve()).as_posix()
        backup_name = f"backup-{index}"
        backup = tx_dir / backup_name
        existed = target.exists()
        if existed:
            shutil.copy2(target, backup)
        entries.append({"path": relative, "backup": backup_name, "existed": existed})

    manifest = {"status": "prepared", "files": entries}
    (tx_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    temporary: dict[Path, Path] = {}
    try:
        for target, value in json_files.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, raw = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
            temp_path = Path(raw)
            with os.fdopen(fd, "wb") as handle:
                handle.write(_json_bytes(value))
                handle.flush()
            temporary[target] = temp_path
        for target, value in text_files.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, raw = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
            temp_path = Path(raw)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(value)
                if value and not value.endswith("\n"):
                    handle.write("\n")
                handle.flush()
            temporary[target] = temp_path

        manifest["status"] = "replacing"
        (tx_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        for target, temp_path in temporary.items():
            os.replace(temp_path, target)
        for target in delete_paths:
            target.unlink(missing_ok=True)
        shutil.rmtree(tx_dir)
    except Exception:
        for temp_path in temporary.values():
            temp_path.unlink(missing_ok=True)
        recover_incomplete_transactions(paths)
        raise
