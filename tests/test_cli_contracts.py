from __future__ import annotations

import json
import unittest
from pathlib import Path

from helpers import TempRepository, run_cli


class CliContractTest(unittest.TestCase):
    """Lock the external CLI contract before command modules are refactored."""

    def setUp(self) -> None:
        self.repo = TempRepository(Path(__file__).resolve().parents[1])

    def tearDown(self) -> None:
        self.repo.close()

    def test_help_exits_zero_and_uses_neoctl_program_name(self) -> None:
        result = run_cli(self.repo.root, "--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: neoctl", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_unknown_command_is_an_argparse_error(self) -> None:
        result = run_cli(self.repo.root, "not-a-command")

        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid choice", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_json_validate_success_shape(self) -> None:
        result = run_cli(self.repo.root, "--json", "validate")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        payload = json.loads(result.stdout)
        self.assertEqual(set(payload), {"ok", "errors", "warnings"})
        self.assertIs(payload["ok"], True)
        self.assertEqual(payload["errors"], [])
        self.assertIsInstance(payload["warnings"], list)

    def test_json_domain_error_shape_and_exit_code(self) -> None:
        result = run_cli(
            self.repo.root,
            "--json",
            "project",
            "create",
            "--title",
            "Test",
            "--slug",
            "test",
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertEqual(
            json.loads(result.stderr),
            {
                "ok": False,
                "error": "project creation requires explicit operator approval and --approve",
            },
        )


if __name__ == "__main__":
    unittest.main()
