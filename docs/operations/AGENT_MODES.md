# Agent modes

`neo` agents must choose a work mode before reading repository content. This prevents repository-development tasks from unnecessarily opening personal operational records and prevents Hermes runtime tasks from ignoring the live workspace state.

## Hermes runtime mode

Use this mode for actual life-day and project operation, including wake and sleep reports, task and milestone status, Calendar work, medication, medical, fridge, notifications, private spark, and messenger actions.

Read first:

1. root `AGENTS.md`;
2. `brief.md`;
3. the active or most recent life-day JSON;
4. the relevant file under `protocols/`;
5. the relevant integration document when an external tool is needed.

Runtime writes use `neoctl`. Do not hand-edit canonical or derived JSON files. Follow the approval and privacy boundaries in `AGENTS.md` and the selected protocol.

## Repository development mode

Use this mode for code, tests, schemas, protocols, configuration, CI, maintained documentation, refactoring, PR preparation, reviews, and repository policy.

Read first:

1. root `AGENTS.md`;
2. [`records/REPO.md`](../../records/REPO.md);
3. [`records/SPEC.md`](../../records/SPEC.md);
4. [`records/STATUS.md`](../../records/STATUS.md);
5. [`records/PLANS.md`](../../records/PLANS.md);
6. relevant ADRs and development documentation.

Do not open or extract contents from the following unless a narrowly scoped task explicitly requires a safe fixture and the operator approves it:

- `brief.md`;
- `data/days/**`;
- `data/projects/**`;
- `data/message-log/**`;
- private records;
- `export/**`;
- `.env`, tokens, credentials, or keyring contents.

Repository-development work should use synthetic test fixtures and non-personal repository documentation. It must not use live operational records as convenient examples.

## Concurrent live operational state

Live runtime work can continue while a repository-development task is in progress. A dirty live checkout is not automatically a blocker: first classify every changed path.

- `data/**` and `brief.md` are operational paths. Runtime-created audit logs, message logs, canonical JSON, indexes, and derived brief output are valid concurrent state when their structure is valid.
- Code, tests, schemas, protocols, configuration, patch artifacts, documentation, repository metadata, credentials, unexpected binaries, symlinks, and paths outside the repository remain non-operational dirty state and block realignment.
- Validate structure without printing operational values. Parse JSON and JSONL, require JSONL objects, run a secret scan, and preserve the current latest state.
- Treat `data/audit/*.jsonl` and `data/message-log/*.jsonl` as append-only: every pre-existing byte and line must remain an exact prefix; truncation or modification is a blocker.
- For mutable operational JSON, require parse and schema validation, preserve existing UUIDs and facts, and retain any valid concurrent additions. Do not compare only to an old SHA.
- Before realignment, create a timestamped backup ref, stage only operational paths, and create a `neoctl:` checkpoint commit. Push that checkpoint through the limited operational-data exception; never include it in a development PR.
- Use a separate clean development worktree for code and policy changes. Preserve the latest operational state during final realignment and do not rebuild `brief.md` or indexes during this workflow.

## Mode selection examples

| Request | Mode |
| --- | --- |
| "일어났어", "오늘 뭐 해야 해?" | Hermes runtime |
| "이 프로젝트 태스크 완료했어" | Hermes runtime |
| "Calendar에 작업 일정 넣어줘" | Hermes runtime |
| "이 PR 리뷰해줘" | Repository development |
| "AGENTS.md 정리해줘" | Repository development |
| "pytest 실패 고쳐줘" | Repository development |
| "schema migration을 설계해줘" | Repository development |

When a request contains both modes, separate the work. Complete repository analysis without reading live personal data, then ask for explicit confirmation before any runtime write.

## Authority

- Root `AGENTS.md` defines the compact entry rules and non-negotiable boundaries.
- `protocols/` defines runtime procedures.
- `records/REPO.md` defines repository workflow and local policy.
- `docs/adr/` records accepted architectural decisions.
- `docs/operations/integrations/` records confirmed external-integration facts and safety limits.
