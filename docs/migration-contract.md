# Migration contract

`neoctl migrate` upgrades persisted documents without changing CLI, approval, privacy, or canonical-data boundaries.

## Required properties

1. **Idempotent steps**
   - Each document migration must report whether it changed the document.
   - Running the same migration again on its own output must report no change and must not advance timestamps.

2. **No in-place mutation**
   - A migration returns a new top-level document.
   - Unknown fields are preserved unless a separately approved migration explicitly removes or renames them.

3. **Timestamp discipline**
   - `updated_at` or `generated_at` changes only when the document changes semantically.
   - Tests use an injected timestamp so first-pass and no-op behavior are deterministic.

4. **One canonical workspace transaction**
   - Changed day, Calendar, and fridge documents are collected first.
   - They are written through one `commit_workspace(...)` call, which validates canonical documents, rebuilds derived files, and uses the existing lock, rollback, and atomic-write behavior.
   - No canonical change means no workspace commit.

5. **Storage-specific migrations remain isolated**
   - Private spark legacy migration keeps its existing dedicated storage procedure and is reported separately.
   - A failure or contract change in a storage-specific migration must not be hidden inside a generic document transformer.

6. **Compatibility**
   - Existing `neo.migrate.calendar_key` and `CATEGORY_MAP` imports remain available.
   - Migration result keys and `neoctl migrate` exit behavior remain unchanged unless a separate compatibility change is approved.

## Adding a migration

- Add or extend a document transformer in `src/neo/migration_steps.py`.
- Preserve source documents and unknown fields.
- Add tests for first-pass change, second-pass no-op, timestamp behavior, and orchestration batching.
- Update schemas only in a separately reviewed change when the persisted contract itself changes.
- Record operator-visible or structural changes in `CHANGELOG.md`.
