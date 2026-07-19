# Repository status

This page records current repository, runtime, and deployment facts that are safe to maintain in source documentation. It intentionally excludes the user's current life-day state, task contents, private events, message-log contents, credentials, and exported personal records.

## Repository state

- The repository contains Python CLI/runtime code under `src/neo/`, schemas under `schemas/`, runtime protocols under `protocols/`, tests under `tests/`, and maintained documentation at the root plus `docs/` and `records/`.
- Operational data is intentionally version-controlled, including `data/message-log/*.jsonl`, but routine operational-data changes are not changelog entries.
- `brief.md`, `data/indexes/*.json`, and other generated runtime views are derived from canonical runtime records and should not be hand-edited.

## Runtime behavior

- `neoctl` is the supported write interface for runtime records.
- Repository transactions validate records, rebuild derived indexes and brief output when needed, and can create `neoctl:` commits.
- `neoctl` automatic push behavior is documented as an existing local divergence from repo-template rather than changed by this repository-records work.

## Deployment reality

- Deployment paths are operator-configured and are not stored in this repository.
- A live clone should follow a reviewed release and remain separate from feature-development worktrees.
- OCI-specific integration checks and deployment verification happen after a change is merged.
- Keyring or Hermes gateway restart procedures that may terminate the active Hermes session must be run directly by the operator over SSH, not from inside the Hermes chat session.

## Unknown or intentionally unstated

This document does not name unconfirmed service units, secrets, deployment commands, recovery steps, or current personal operational state. Add those only when they are confirmed by non-personal repository documentation and are safe to publish in this repository.
