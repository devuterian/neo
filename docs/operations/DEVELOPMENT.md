# Development workflow

Repository-development changes use ordinary Git branches and pull requests. This includes code, tests, schemas, protocols, configuration, CI, and maintained documentation.

## Local setup and validation

Use the root [`BOOTSTRAP.md`](../../BOOTSTRAP.md) for installation and Hermes setup context. For repository-development PRs, report only commands actually run. Common safe checks include:

```bash
python -m pip install -e '.[dev]'
pytest -q
git diff --check
```

Run `neoctl --json validate` only when the environment is safe for read-only validation and when doing so does not require opening or mutating forbidden operational data for the task at hand. If it is unsafe, report it as blocked.

## Pull request expectations

- Keep changes reviewable and scoped.
- Follow [ADR 0001](../adr/0001-refactoring-contracts.md) for refactoring and public-contract preservation.
- Update [`CHANGELOG.md`](../../CHANGELOG.md) when the change affects user-visible behavior, operator workflow, structure, security, privacy, or repository policy under [`docs/changelog-policy.md`](../changelog-policy.md).
- Do not include personal operational record contents in changelog or documentation.

## Runtime commits are different

`neoctl` may create `neoctl:` commits for operational data and derived runtime files. That limited direct-push path is not the workflow for maintained repository-development changes.
