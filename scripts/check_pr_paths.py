#!/usr/bin/env python3
"""Reject pull-request changes to live operational and generated paths."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Iterable, Sequence

PROTECTED_EXACT = {".env", "brief.md"}
PROTECTED_PREFIXES = ("data/", "export/")


def normalize_path(path: str) -> str:
    """Normalize a Git path for policy matching."""

    return path.strip().replace("\\", "/").removeprefix("./")


def is_protected_path(path: str) -> bool:
    """Return whether a repository-relative path is protected in PRs."""

    normalized = normalize_path(path)
    return normalized in PROTECTED_EXACT or normalized.startswith(PROTECTED_PREFIXES)


def protected_paths(paths: Iterable[str]) -> list[str]:
    """Return sorted unique protected paths from an iterable."""

    return sorted({normalize_path(path) for path in paths if is_protected_path(path)})


def changed_paths(base: str, head: str) -> list[str]:
    """Read changed paths from Git using a three-dot comparison."""

    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMRD", f"{base}...{head}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "git diff failed"
        raise RuntimeError(detail)
    return [line for line in result.stdout.splitlines() if line.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fail when a pull request changes live operational paths."
    )
    parser.add_argument("--base", required=True, help="Base commit SHA or ref")
    parser.add_argument("--head", default="HEAD", help="Head commit SHA or ref")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        changed = changed_paths(args.base, args.head)
    except RuntimeError as exc:
        print(f"Unable to inspect pull-request paths: {exc}", file=sys.stderr)
        return 2

    blocked = protected_paths(changed)
    if blocked:
        print("Pull requests must not change live operational or generated paths:")
        for path in blocked:
            print(f"- {path}")
        print()
        print(
            "Use neoctl for runtime data writes. Keep development PRs limited "
            "to code, tests, schemas, protocols, configuration, CI, and "
            "maintained documentation."
        )
        return 1

    print(f"PR path guard passed: {len(changed)} changed path(s), none protected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
