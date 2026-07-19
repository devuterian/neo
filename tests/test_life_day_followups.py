from __future__ import annotations

import json
from pathlib import Path

from helpers import TempRepository, run_cli


def test_followup_after_next_wake_targets_original_life_day() -> None:
    repo = TempRepository(Path(__file__).resolve().parents[1])
    try:
        assert run_cli(repo.root, "--json", "day", "wake", "--at", "2026-07-10T08:00:00+09:00").returncode == 0
        assert run_cli(repo.root, "--json", "day", "wake", "--at", "2026-07-11T09:00:00+09:00").returncode == 0

        for command in (
            ("day", "--date", "2026-07-10", "med", "take", "--name", "약 B", "--at", "2026-07-11T01:00:00+09:00"),
            ("day", "--date", "2026-07-10", "mood", "set", "--summary", "괜찮음"),
            ("day", "--date", "2026-07-10", "outing", "go", "--place", "카페", "--at", "2026-07-10T20:00:00+09:00"),
        ):
            result = run_cli(repo.root, "--json", *command)
            assert result.returncode == 0, result.stderr

        previous = json.loads((repo.root / "data/days/2026/2026-07-10.json").read_text(encoding="utf-8"))
        current = json.loads((repo.root / "data/days/2026/2026-07-11.json").read_text(encoding="utf-8"))
        assert previous["medications"][0]["name"] == "약 B"
        assert previous["mood"]["summary"] == "괜찮음"
        assert previous["outings"][0]["place"] == "카페"
        assert current["medications"] == []
        assert current["mood"] is None
        assert current["outings"] == []
    finally:
        repo.close()
