from __future__ import annotations

import unittest

import neo.cli as cli
from neo.cli_days import handle_day
from neo.cli_parser import build_parser
from neo.cli_projects import handle_project
from neo.cli_support import resolve_day_or_auto_wake


class CliBoundaryTest(unittest.TestCase):
    def test_legacy_module_reexports_parser(self) -> None:
        self.assertIs(cli.build_parser, build_parser)

    def test_legacy_module_reexports_auto_wake_helper(self) -> None:
        self.assertIs(cli.resolve_day_or_auto_wake, resolve_day_or_auto_wake)

    def test_legacy_module_reexports_domain_handlers(self) -> None:
        self.assertIs(cli.handle_project, handle_project)
        self.assertIs(cli.handle_day, handle_day)

    def test_parser_preserves_global_and_nested_option_positions(self) -> None:
        args = build_parser().parse_args(
            [
                "--json",
                "--auto-wake",
                "always",
                "day",
                "--date",
                "2026-07-10",
                "meal",
                "add",
                "--tag",
                "lunch",
                "--what",
                "sample",
            ]
        )
        self.assertTrue(args.json)
        self.assertEqual(args.auto_wake, "always")
        self.assertEqual(args.command, "day")
        self.assertEqual(args.date, "2026-07-10")
        self.assertEqual(args.day_command, "meal")
        self.assertEqual(args.meal_command, "add")
        self.assertEqual(args.tag, "lunch")
        self.assertEqual(args.what, "sample")

    def test_parser_preserves_private_list_json_destination(self) -> None:
        args = build_parser().parse_args(
            ["private", "spark", "list", "--json", "--last", "7d"]
        )
        self.assertFalse(args.json)
        self.assertTrue(args.spark_json)
        self.assertEqual(args.last, "7d")


if __name__ == "__main__":
    unittest.main()
