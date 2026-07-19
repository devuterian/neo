# Live operational checkpoints

This document is the canonical procedure for preserving runtime changes that appear in the live `neo` checkout while repository-development work is in progress.

## Scope and classification

Classify the complete live diff before deciding whether work can continue.

Operational paths are `data/**` and `brief.md`. This includes runtime-created `data/audit/*.jsonl`, `data/message-log/*.jsonl`, canonical JSON, `data/indexes/**`, and generated brief output. These paths represent concurrent runtime state and are not automatically blockers.

Non-operational paths include code, tests, schemas, protocols, configuration, patch artifacts, maintained documentation, repository metadata, and any path outside the repository. `.env`, credentials, tokens, keys, unexpected binaries, and symlinks are sensitive or risky and block the workflow unless explicitly handled by a separate approved procedure.

## Checkpoint procedure

1. Inspect the complete status and changed-path list. Do not read or print personal record values.
2. Confirm every changed operational file is a regular file inside the repository. Reject unexpected binaries and symlinks.
3. Parse JSON files and require every non-empty JSONL line to be a JSON object. Validate required structural keys and run a secret scan without printing values.
4. For `data/audit/*.jsonl` and `data/message-log/*.jsonl`, compare against any known previous version as bytes or lines. The previous content must be an exact prefix; truncation or modification is a blocker. A new file or appended lines are valid runtime state.
5. For mutable operational JSON, validate the latest file and preserve existing UUIDs and facts. A valid concurrent addition is part of the latest state; an old SHA is not a requirement.
6. Create a timestamped backup ref before staging.
7. Stage only the validated operational paths and run `git diff --cached --check`.
8. Commit with a `neoctl:` subject and push through the limited operational-data exception. Never include the checkpoint in a code, policy, or feature PR.

## Development and final realignment

Create code and policy work in a separate clean worktree from the latest `origin/main`. During development, recheck the live checkout at checkpoints and repeat the classification procedure if new runtime state appears.

After a development PR is merged, preserve the latest operational state while realigning the live branch. Create a new backup ref, checkpoint any operational-only changes, then rebase or fast-forward the live branch as appropriate. Abort on conflict if preservation of operational facts, UUIDs, or append-only prefixes cannot be proven. Do not squash operational commits, regenerate `brief.md`, rebuild indexes, or push live-only operational commits as part of the development merge.

## Blocking conditions

Stop and preserve the current state if operational and non-operational changes cannot be separated, an operational file is invalid, an append-only prefix changed, a sensitive file appeared, an unexpected binary or symlink is present, or a merge conflict makes operational preservation uncertain.

Operational file contents, audit values, credentials, tokens, and personal records must not be copied into PR descriptions, changelogs, or user-facing reports.
