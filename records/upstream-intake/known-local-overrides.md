# Known local overrides from repo-template

These differences are intentional local policy for `neo` and should not be overwritten by future upstream-template intake.

1. `neo` does not adopt repo-template's `commit-generator`, `LOG-*` identifiers, `prepare-commit-msg` hook, or `commit-msg` hook.
2. `neoctl` currently creates `neoctl:` commits using `git commit -m` and pushes runtime changes automatically.
3. Limited direct push to `main` is allowed only for `neoctl`-generated operational-data and derived-file commits.
4. Code, tests, schemas, protocols, configuration, CI, and maintained documentation must be changed through pull requests.
5. Operational data, including `data/message-log/*.jsonl`, remains intentionally version-controlled.
6. Existing `docs/adr/` remains the canonical decision-record location; do not create a duplicate `records/decisions/` tree.
7. Existing `protocols/` remains the canonical runtime-procedure location.
8. `records/STATUS.md`, `PLANS.md`, and `INBOX.md` describe repository development and operation, not the user's live personal state.
9. This repository-records PR does not restructure root `AGENTS.md`; runtime/development instruction routing is a separate follow-up PR.
