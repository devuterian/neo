from pathlib import Path
from runpy import run_path

MODULE = run_path(
    str(Path(__file__).resolve().parents[1] / "scripts" / "check_pr_paths.py"),
    run_name="check_pr_paths_test",
)

normalize_path = MODULE["normalize_path"]
is_protected_path = MODULE["is_protected_path"]
protected_paths = MODULE["protected_paths"]


def test_normalize_path() -> None:
    assert normalize_path("./data\\days\\today.json") == "data/days/today.json"


def test_live_operational_paths_are_protected() -> None:
    assert is_protected_path("data/days/2026/2026-07-10.json")
    assert is_protected_path("data/message-log/2026-07-10.jsonl")
    assert is_protected_path("brief.md")
    assert is_protected_path("export/report.md")
    assert is_protected_path(".env")


def test_repository_development_paths_are_allowed() -> None:
    assert not is_protected_path("src/neo/workspace.py")
    assert not is_protected_path("tests/fixtures/data/example.json")
    assert not is_protected_path("docs/operations/README.md")
    assert not is_protected_path(".env.example")


def test_protected_paths_are_sorted_and_unique() -> None:
    assert protected_paths(
        ["brief.md", "data/example.json", "brief.md", "src/neo/example.py"]
    ) == ["brief.md", "data/example.json"]
