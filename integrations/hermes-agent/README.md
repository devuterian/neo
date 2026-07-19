# Hermes Agent integration

Neo can be used as a Hermes Agent workspace, but the public repository does not ship patches captured from a specific production server.

## Generic contract

A Hermes integration should:

- receive the Neo workspace path from deployment configuration;
- run only the workspace's fixed `.venv/bin/neoctl` executable;
- keep Telegram tokens, allowed chat IDs, and owner user IDs in environment variables;
- treat the authenticated owner as a configurable identity, never a hard-coded name;
- expose read-only group status separately from owner-only mutations;
- exclude raw files, message logs, private records, shell access, and credentials from group tools;
- require a scoped confirmation before destructive mutations;
- record an explicit sleep report before optional follow-up questions;
- avoid claiming access to Telegram history outside the current update and reply quote.

## Suggested environment

```dotenv
NEO_ROOT=/absolute/path/to/neo
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USERS=
TELEGRAM_TRUSTED_GROUP_OWNER_USER_ID=
TELEGRAM_ALLOWED_GROUP_CHATS=
```

Hermes versions change independently. Verify adapter APIs against the installed Hermes version instead of applying an old production diff blindly.
