from __future__ import annotations

import argparse
import json
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

from helpers import TempRepository
from neo.cli_operations import handle_fridge
from neo.domain import fridge as fridge_domain
from neo.utils import SEOUL, today_seoul


class SeoulDateBoundaryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = TempRepository(Path(__file__).resolve().parents[1])

    def tearDown(self) -> None:
        self.repo.close()

    def test_today_seoul_uses_canonical_clock(self) -> None:
        clock = datetime(2026, 7, 11, 0, 30, tzinfo=SEOUL)
        with patch("neo.utils.now_seoul", return_value=clock):
            self.assertEqual(today_seoul(), date(2026, 7, 11))

    def test_fridge_expiry_uses_seoul_date(self) -> None:
        fridge = fridge_domain.create_fridge()
        fridge = fridge_domain.add_item(
            fridge,
            "expires today",
            expires_at="2026-07-10",
        )
        fridge = fridge_domain.add_item(
            fridge,
            "expires tomorrow",
            expires_at="2026-07-11",
        )
        self.repo.paths.fridge_file.write_text(
            json.dumps(fridge, ensure_ascii=False),
            encoding="utf-8",
        )
        args = argparse.Namespace(fridge_command="expired")
        with patch("neo.cli_operations.today_seoul", return_value=date(2026, 7, 10)):
            result = handle_fridge(self.repo.paths, args)
        self.assertEqual(
            [item["name"] for item in result["items"]],
            ["expires today"],
        )


if __name__ == "__main__":
    unittest.main()
