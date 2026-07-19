---
name: upstream-intake
description: Review LPFchan/repo-template changes against neo local contracts.
argument-hint: Upstream commit, release, file, feature, or review range
---

# Upstream intake

Use this skill when reviewing changes from `LPFchan/repo-template`. The upstream repository is a structural reference, not authority over `neo`.

Read first:

- `records/REPO.md`;
- `records/upstream-intake/README.md`;
- `records/upstream-intake/known-local-overrides.md`;
- `records/upstream-intake/compatibility-watchlist.md`;
- relevant local ADRs and implementation files.

## Output

A concise review that classifies each material upstream idea as:

- **Adopt** — compatible with local contracts with minimal adaptation;
- **Adapt** — useful, but must be changed for local runtime or repository policy;
- **Defer** — potentially useful, but no current need or prerequisite;
- **Reject** — conflicts with local contracts, privacy, runtime operation, or scope.

## Procedure

1. Define the upstream scope.
   - Record the repository, commit, release, PR, or file range reviewed.
   - Do not copy the entire upstream scaffold into the local repository.

2. Identify material changes.
   - document structure and authority;
   - agent routing;
   - commit policy and hooks;
   - IDs and provenance requirements;
   - upstream-review workflows;
   - skills and automation;
   - compatibility or migration assumptions.

3. Compare against local contracts.
   - `neoctl:` runtime commits and automatic push behavior;
   - intentional version control of operational data;
   - `docs/adr/` as decision authority;
   - `protocols/` as runtime-procedure authority;
   - Hermes runtime versus repository-development read boundaries;
   - CLI, schema, privacy, and approval contracts.

4. Apply standing local overrides.
   - Reject commit-generator, `LOG-*`, prepare-commit-msg, and commit-msg enforcement unless a separate approved ADR changes the runtime commit model.
   - Adapt upstream decision-record proposals to `docs/adr/`.
   - Adapt runtime procedures to `protocols/`.
   - Keep STATUS, PLANS, and INBOX repository-focused.

5. Record the result.
   - Create a focused report under `records/upstream-intake/reports/` when the review is concrete and reusable.
   - Include upstream reference, affected local contracts, classification, rationale, and follow-up PR or issue.
   - Update the watchlist or known overrides only when durable policy changes.

6. Implement separately.
   - Do not mix a broad upstream survey with unrelated implementation.
   - Use small PRs for adopted or adapted changes.

## Stop conditions

Stop and ask for judgment when an upstream change would:

- replace the `neoctl` runtime commit path;
- remove version control from operational data;
- alter canonical data or Calendar authority;
- weaken privacy or approval boundaries;
- introduce a second decision or runtime-procedure authority;
- require a migration whose effect is not documented.

## Quality bar

- exact upstream reference;
- local-contract-first reasoning;
- explicit adopt/adapt/defer/reject decisions;
- no wholesale scaffold copy;
- no secrets or personal operational records;
- implementation isolated in follow-up PRs.
