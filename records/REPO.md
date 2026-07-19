# Repository operating model

`neo` is a JSON-based Hermes workspace and Python CLI repository. This document describes how repository changes are made and where durable repository documents live. It does not contain personal life-day state, project task contents, private events, message logs, credentials, or exported records.

## Authority and canonical surfaces

- Agent entry and mode routing: root [`AGENTS.md`](../AGENTS.md) selects Hermes runtime or repository-development mode; [`docs/operations/AGENT_MODES.md`](../docs/operations/AGENT_MODES.md) defines their read boundaries.
- Repository procedures: [`skills/`](../skills/) stores reusable development workflows. Skills do not replace repository policy, system truth, ADRs, or runtime protocols.
- Runtime procedure authority: [`protocols/`](../protocols/) remains the canonical location for life-day, project, Calendar, notification, and other Hermes operating procedures.
- Architecture decisions: [`docs/adr/`](../docs/adr/) remains the canonical decision-record tree. Do not create a parallel `records/decisions/` tree.
- Changelog policy: [`docs/changelog-policy.md`](../docs/changelog-policy.md) defines which user-visible, structural, security, privacy, and operator-facing changes are recorded in [`CHANGELOG.md`](../CHANGELOG.md).
- Repository records: `records/` separates repository policy, durable specification, current repository status, accepted plans, untriaged development capture, reusable research, and upstream-template review.
- Operations documentation: [`docs/operations/`](../docs/operations/) gives a non-secret entry point for development, OCI live-clone, deployment, agent modes, and integration operations.

## Change workflow

Code, tests, schemas, protocols, configuration, CI, and maintained documentation change through branches and pull requests. Refactoring work follows [ADR 0001](../docs/adr/0001-refactoring-contracts.md): keep public CLI contracts stable unless a separate approved change replaces them, keep changes small, and avoid live operational data edits in structural PRs.

Pull requests should report only checks that actually ran. If a validation command would require unsafe access to live operational data, report it as blocked rather than guessing a result.

Repository-development agents do not perform Hermes runtime session boot. They read repository records, relevant skills, and development documents instead of `brief.md` or live personal records.

## Limited direct-push exception

`neoctl` currently commits operational changes from repository transactions by running `git commit -m` with a `neoctl:` subject and then pushing to the current branch. This behavior is part of the runtime workspace contract in `src/neo/workspace.py`.

Limited direct push to `main` is allowed only for `neoctl`-generated operational-data and derived-file commits. This exception covers ordinary runtime records and reproducible runtime outputs such as `data/**`, `data/message-log/*.jsonl`, `data/indexes/**`, and `brief.md` when they are produced by `neoctl`.

If a runtime-created operational file was previously uncommitted when a repository task starts, a safe checkpoint may capture it with a `neoctl:` commit after structural, append-only, and secret validation. This checkpoint remains separate from every development PR. The current latest operational state is authoritative; an old file SHA is not by itself a preservation requirement.

This includes `data/audit/*.jsonl` and other runtime-created files under `data/**`; it does not expand the exception to code, tests, configuration, patch artifacts, or maintained documentation.

The exception does not apply to code, tests, schemas, protocols, configuration, CI, maintained documentation, hooks, or repository policy files. Those changes require pull requests.

## Local divergence from `LPFchan/repo-template`

This repository adapts the template's document-separation and selected procedural-skill ideas but intentionally does not copy its scaffold wholesale.

1. `neo` does not adopt repo-template's `commit-generator`, `LOG-*` identifiers, `prepare-commit-msg` hook, or `commit-msg` hook.
2. `neoctl` currently creates `neoctl:` commits using `git commit -m` and pushes runtime changes automatically.
3. Limited direct push to `main` is allowed only for `neoctl`-generated operational-data and derived-file commits.
4. Code, tests, schemas, protocols, configuration, CI, and maintained documentation must be changed through pull requests.
5. Operational data, including `data/message-log/*.jsonl`, remains intentionally version-controlled.
6. Existing `docs/adr/` remains the canonical decision-record location; do not create a duplicate `records/decisions/` tree.
7. Existing `protocols/` remains the canonical runtime-procedure location.
8. `records/STATUS.md`, `records/PLANS.md`, and `records/INBOX.md` describe repository development and operation, not the user's live personal state.
9. Root `AGENTS.md` is a compact router. Detailed runtime procedures and integration facts remain in their canonical documents rather than being duplicated in the root instruction file.
10. Local skills are procedural only. They do not introduce commit provenance enforcement, prototype-mode, or mandatory daily inbox review.

## Document map

- [`SPEC.md`](SPEC.md): durable system boundaries and canonical data model.
- [`STATUS.md`](STATUS.md): current repository, runtime, and deployment reality that is safe to maintain in documentation.
- [`PLANS.md`](PLANS.md): accepted repository-development direction.
- [`INBOX.md`](INBOX.md): untriaged repository-development ideas and defects.
- [`research/`](research/): curated reusable technical research.
- [`upstream-intake/`](upstream-intake/): recurring review of `LPFchan/repo-template` changes.
- [`../skills/`](../skills/): reusable repository-development procedures.
