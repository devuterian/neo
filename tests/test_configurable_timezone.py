from datetime import datetime
from unittest.mock import patch

from neo.utils import local_timezone, now_seoul, parse_datetime


def test_timezone_can_be_configured_with_environment(monkeypatch):
    monkeypatch.setenv("NEO_TIMEZONE", "America/New_York")
    assert str(local_timezone()) == "America/New_York"
    with patch("neo.utils.datetime") as clock:
        clock.now.return_value = datetime(2026, 7, 20, 12, 0)
        now_seoul()
        clock.now.assert_called_once_with(local_timezone())


def test_naive_datetime_uses_configured_timezone(monkeypatch):
    monkeypatch.setenv("NEO_TIMEZONE", "Europe/Paris")
    parsed = parse_datetime("2026-07-20T12:00:00")
    assert str(parsed.tzinfo) == "Europe/Paris"
