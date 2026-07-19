# Repository plans

이 문서는 `neo` 저장소의 승인된 개발 방향을 기록한다. 개인 생활 일정, 프로젝트 납기, 생활일 계획은 기록하지 않는다.

## Completed

### Define document migration steps

- Delivered by PR #13.
- Day, Calendar, and fridge migrations are non-mutating document transformers with explicit changed/no-op results.
- Second-pass idempotency, timestamp discipline, compatibility exports, and one-workspace-commit batching are covered by tests.
- The durable extension rules are documented in `docs/migration-contract.md`.

### Centralize Seoul date defaults

- Delivered by PR #12.
- `today_seoul()` is the canonical date-only clock for runtime defaults.
- medical cycle calculations, default injection dates, and fridge expiry checks no longer depend on the host process timezone.
- Explicit dates passed by callers remain unchanged.

### Add a typed repository lookup catalog

- Delivered by PR #11.
- Project and task resolution now use one read-only snapshot catalog built from a single project-file load.
- Repository location types and JSON document aliases have an explicit module boundary.
- Existing ID, slug, case-insensitive title, ambiguity, and compatibility-import behavior remains unchanged.

### Modularize the CLI boundary

- Delivered by PR #10.
- Parser construction, shared support helpers, project handlers, life-day handlers, and operational handlers now live in focused modules.
- `neo.cli` remains the console entry point and compatibility facade for existing imports.
- Command names, option placement, exit codes, JSON response shapes, approval requirements, and runtime write behavior remain unchanged.

### Isolate workspace persistence boundaries

- Delivered by PR #9.
- `commit_workspace(...)` keeps its public keyword contract while normalizing updates into a `WorkspaceChangeSet`.
- Derived-output generation, cross-record validation, and runtime Git synchronization now have separate modules.
- Locking, rollback recovery, atomic replacement, canonical data, and `neoctl:` auto-push behavior remain unchanged.

### Repository operating model

- Delivered by PR #5.
- Added `records/`, `docs/operations/`, upstream-intake boundaries, OCI live-clone policy, and the limited `neoctl:` direct-push exception.

### Split agent runtime and development routing

- Delivered by PR #6.
- Root `AGENTS.md` now selects Hermes runtime or repository-development mode before reading workspace files.
- Repository-development mode must not read live personal records.

### Protect live operational paths in pull requests

- Delivered by PR #7.
- A PR-only CI guard rejects root `data/**`, `brief.md`, `export/**`, and `.env` changes.
- The guard lists prohibited paths without reading file contents and does not run on `main` pushes.

### Add selected repository skills

- Delivered by PR #8.
- Added locally adapted `repo-orchestrator`, `upstream-intake`, `clean-correction-gate`, and `sharpen-the-tip` procedures.
- Skills remain procedural; policy stays in `records/REPO.md`, system truth in `records/SPEC.md`, decisions in `docs/adr/`, and runtime procedures in `protocols/`.
- Commit-generator, `LOG-*`, commit hooks, prototype-mode, and mandatory daily inbox review remain excluded.

## Accepted future work

No additional repo-template adaptation is currently approved. New ideas should enter through `records/INBOX.md` and be promoted only after review.

Daily inbox pressure review remains deferred until repository capture volume creates a recurring triage problem.

## Ongoing constraints

- Keep PRs small and focused.
- Do not modify live operational data in repository-development PRs.
- Preserve CLI, canonical data, Calendar, approval, and privacy contracts.
- Update `CHANGELOG.md` when repository policy or operator workflow changes.
- Report only verification that actually ran.
