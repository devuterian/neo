# System specification

This document records durable system and data-boundary contracts for `neo`. It is not a copy of live personal records and must not include life-day notes, project task contents, private events, message logs, credentials, or token values.

## System purpose

`neo` is a JSON-based workspace for operating Hermes life-day and project workflows through `neoctl`. It keeps two canonical runtime record families independent:

- `day`: a life-day that starts with a wake report and continues until the next wake transition. Midnight is not the boundary.
- `project`: a long-running work unit with milestones and tasks.
- `someday`: an optional, date-independent action-item store; it is not a day todo or a pending obligation.

A life-day may reference selected project tasks and work sessions, but neither record family is a derivative of the other.

## Canonical runtime records

Project records live under `data/projects/*.json` and own project titles, statuses, milestones, tasks, remaining milestone effort, linked Calendar event IDs, waiting or pause reasons, and project decision records.

Supporting persistent records include `data/pending.json` for obligations and `data/someday.json` for optional candidates. A missing someday store is a normal empty state.

Life-day records live under `data/days/YYYY/YYYY-MM-DD.json`, where the filename uses the calendar date of wake. They own wake and sleep reports, workday type, selected tasks for that day, planned allocation, check-ins and check-outs, external schedule snapshots captured at planning time, and life-day notes.
## Medication event model (day schema v2)

Life-day medications are an event record array (schema_version 2). Each element is an independent medication event with the following shape:

- `medication_id` — required UUID for each event
- `name` — non-empty string; same name may appear in multiple events
- `action` — `taken` or `skipped`
- `occurred_at` — date-time or null (the actual medication take/skip/application time, when known)
- `recorded_at` — required date-time (when the event was entered into the system; never a fallback for `occurred_at`)
- `dose` — string or null (e.g. `1정`, `5mg`)
- `note` — string or null

Key invariants:

- Same-name medication events are allowed (repeated doses).
- Name-based uniqueness is not enforced.
- `occurred_at` is the canonical timestamp for user-facing event dates and times. Convert it to `Asia/Seoul` before deriving a calendar date.
- `day.date` and the day filename identify the life-day storage container, not the medication event's calendar date.
- A null `occurred_at` remains an unknown actual time; it must not be filled from `recorded_at`, `day.date`, filename, message-log, notes, or reply timestamps.
- The events array starts empty on a new life day.
- The public workspace has no expected medication names. A deployment may add its own reminder policy without storing placeholder events.
- Legacy `taken`/`taken_at` fields are migrated to the event shape via deterministic UUID5 identifiers.
- Placeholders (`taken=false`, no meaningful note) are removed during migration.
- Day notes are never auto-parsed into medication events.


Both project and life-day records use UUIDs for project, milestone, task, and nested record identity as defined by the schemas and validation code.

## Calendar authority

Google Calendar is the canonical source for external schedules, milestone dates, final due dates, and planned work events. Project JSON stores linked Google event IDs instead of copying dates or due dates. Calendar reads may produce indexes or snapshots, but if Calendar cannot be read, documentation and runtime summaries must not guess dates, remaining days, or schedule slack.

## Derived files and generated views

`data/indexes/*.json` and `brief.md` are reproducible derived files. They are version-controlled as part of the operational workspace, but they are not hand-edited. Derived files are rebuilt by `neoctl` or repository functions that validate and write through the transaction boundary.

## Write boundary

Runtime writes under `data/` go through `neoctl` and the repository transaction boundary. Direct JSON editing is not the supported operational path. `neoctl` may update canonical runtime records, rebuild derived files, create `neoctl:` commits, and push those runtime changes automatically.

Documentation and code changes are normal repository-development changes and use branches and pull requests.

## Approval and privacy constraints

Approval requirements for project creation, major state changes, milestone effort changes, destructive actions, and Calendar writes are part of the runtime operating contract. Explicitly reported factual events such as wake, sleep, check-in, check-out, task additions, status reports, and notes may be recorded through `neoctl` without a separate approval prompt when the relevant protocol allows it.

Private and sensitive records remain excluded from ordinary `brief.md`, Calendar output, public status, and group projections. `private spark` is stored and reported through its dedicated command path and must not be copied into general repository records, changelog entries, or operations documentation.
