# ADR 0001: Refactoring contracts

- Status: Accepted
- Date: 2026-07-10

## Context

`neo` stores live operational data while the Python application, CLI, generated indexes, brief renderer, validation, and Git synchronization continue to evolve. Structural changes must not rewrite operational data or silently change the interface used by Hermes.

## Decision

Refactoring work will be delivered as small pull requests with one structural concern per PR. Existing behavior is protected with characterization tests before code is moved.

The following contracts remain stable unless a separate approved change explicitly replaces them:

- `neoctl` command names, option placement, exit codes, and JSON response shapes
- `data/projects/*.json` and `data/days/YYYY/*.json` as independent canonical records
- Google Calendar as the canonical source for project and milestone dates
- `data/indexes/*.json` and `brief.md` as reproducible derived files
- all writes under `data/` passing through `neoctl` and the repository transaction boundary
- repository locking, rollback recovery, and atomic replacement semantics
- approval requirements defined in `AGENTS.md`
- operational data, including `data/message-log/*.jsonl`, remaining version-controlled
- private data remaining excluded from ordinary brief, Calendar, public status, and group projections

## Pull request rules

Each refactoring PR must:

1. avoid edits to live files under `data/`, `brief.md`, and `export/`;
2. add or preserve tests for the interface being moved;
3. keep migration and schema compatibility explicit;
4. report validation that was actually run, without claiming unavailable checks;
5. remain reviewable independently and avoid unrelated feature changes.

## Verification baseline

The expected local verification commands are:

```bash
python -m pip install -e '.[dev]'
pytest -q
neoctl validate
neoctl doctor
```

`neoctl validate` and `neoctl doctor` must be run against an isolated fixture or an intentional operator environment. Tests must never copy or mutate the repository's live `data/` tree.

## Consequences

Refactoring may require more PRs and temporary adapter code. In return, regressions can be attributed to a small diff, and live operational records stay outside structural cleanup commits.
