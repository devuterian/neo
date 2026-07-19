---
name: repo-orchestrator
description: Route repository-development work to the correct neo artifact and execution surface.
argument-hint: Task, defect, research question, policy change, or maintenance request
---

# Repository orchestrator

Use this skill only in repository-development mode. Read root `AGENTS.md` and `records/REPO.md` first. Do not read live personal operational records to classify repository work.

## Output

- one clear destination for each distinct kind of repository information;
- deliberate separation of durable truth, current status, accepted plans, untriaged capture, research, decisions, runtime procedures, and implementation history;
- escalation only when a real policy or compatibility judgment is required.

## Procedure

1. Classify the request.
   - Durable system or data-boundary truth → `records/SPEC.md`.
   - Current repository, runtime, or deployment reality → `records/STATUS.md`.
   - Accepted future repository direction → `records/PLANS.md`.
   - Untriaged repository idea or defect → `records/INBOX.md`.
   - Reusable technical investigation → `records/research/`.
   - Accepted architectural decision → `docs/adr/`.
   - Hermes runtime procedure → `protocols/`.
   - Confirmed non-secret operator procedure → `docs/operations/`.
   - Recurring repo-template review → `records/upstream-intake/`.
   - Implementation history → Git commits and pull requests.
   - Live runtime operational checkpoint → [`docs/operations/LIVE_OPERATIONAL_CHECKPOINTS.md`](../../docs/operations/LIVE_OPERATIONAL_CHECKPOINTS.md); keep it separate from implementation artifacts.

2. Read the destination guide before writing.
   - Use the directory README when present.
   - Preserve the authority map in `records/REPO.md`.

3. Keep layers separate.
   - Do not promote speculation directly into `records/PLANS.md`.
   - Do not use `records/STATUS.md` as a personal status dashboard.
   - Do not store raw transcripts or execution logs as research.
   - Do not duplicate ADRs under `records/decisions/`.
   - Do not duplicate runtime procedures from `protocols/` into agent instructions.

4. Split cross-layer work deliberately.
   - A research memo may lead to an ADR and then a plan.
   - A merged implementation may update STATUS and CHANGELOG.
   - Each artifact must have a distinct purpose; do not copy the same evolving text everywhere.
   - If live operational state changes concurrently, follow the checkpoint procedure before final realignment and keep operational commits out of development branches.

5. Apply repository workflow.
   - Use a focused branch and pull request for maintained files.
   - Keep live operational paths out of repository-development changes.
   - Update `CHANGELOG.md` when policy, structure, compatibility, security, privacy, or operator workflow changes.
   - Report only checks that actually ran.

## Escalate when

- public CLI or JSON contracts would change;
- canonical data or Calendar authority would change;
- privacy or approval boundaries conflict;
- a new schema or migration is required;
- a proposed repo-template feature conflicts with a known local override;
- the correct artifact boundary remains ambiguous after reading local policy.

## Quality bar

- clear routing;
- no personal operational-data leakage;
- no duplicate authority;
- small, reviewable changes;
- explicit facts versus recommendations;
- no commit-generator, `LOG-*`, or hook requirements.
