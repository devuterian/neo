# Compatibility watchlist

Use this watchlist when reviewing future `LPFchan/repo-template` changes. It identifies areas where upstream ideas may conflict with local `neo` contracts.

## Commit provenance and hooks

Template changes around commit generators, `LOG-*` identifiers, prepare-commit hooks, commit-msg hooks, or automatic enforcement require explicit rejection or adaptation. They conflict with the current `neoctl:` runtime commit path unless a separate approved change replaces that behavior.

## Decision-record layout

Template changes that introduce `records/decisions/` should be adapted to the existing [`docs/adr/`](../../docs/adr/) tree.

## Runtime procedures

Template changes that move operational procedures should be adapted to keep [`protocols/`](../../protocols/) as the runtime-procedure authority.

## Operational data policy

Template assumptions that operational data should be excluded from version control must be reviewed against ADR 0001 and local policy: operational data, including `data/message-log/*.jsonl`, is intentionally version-controlled.

## Documentation scope

Template status, plan, and inbox documents must be kept repository-focused here. They must not become another copy of personal life-day state, project-management data, private records, or message logs.
