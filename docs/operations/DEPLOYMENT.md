# Deployment

1. Install Neo in a stable directory.
2. Run `neoctl init` and configure the local, ignored `config/app.json`.
3. Keep tokens and credentials in the deployment environment.
4. Back up `data/` before upgrading.
5. Run `pytest -q` and `neoctl --json validate` before connecting an agent.

Runtime data and application source may use separate private and public Git remotes. Never push personal runtime data to the public Neo repository.
