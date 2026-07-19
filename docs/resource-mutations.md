# Resource mutation registry

The typed neoctl resource interface covers authoritative source records without accepting raw documents, paths, JSON pointers, or shell commands.

| Schema | Kind | Stable resource | Mutation capability |
| --- | --- | --- | --- |
| app.schema.json | authoritative | app | update/correct/delete; delete resets the singleton |
| day.schema.json | authoritative | day | add/update/correct/delete |
| project.schema.json | authoritative | project | add/update/correct/delete |
| pending.schema.json | authoritative | pending | add/update/correct/delete |
| someday.schema.json | authoritative | someday | add/update/correct/delete |
| fridge.schema.json | authoritative | fridge | add/update/correct/delete |
| medical.schema.json | authoritative | medical | add/update/correct/delete |
| current-index.schema.json | derived | current-index | read/list, rebuild/validate |
| project-index.schema.json | derived | project-index | read/list, rebuild/validate |
| calendar-index.schema.json | derived | calendar-index | read/list, rebuild/validate |
| action-item.schema.json | embedded | action-item | parent day/pending/someday/project operation only |
| private-spark.schema.json | private | private-spark | local private command boundary only; never trusted-group exposed |

Every schema file must appear exactly once in the registry. Mutations resolve a typed resource and target, enforce immutable fields and an optional revision, validate the full workspace, regenerate derived output through the existing transaction, and return a normalized result. Delete requires --confirm and a reason. Correct is distinct from update: it requires a reason and returns before/after summaries for the corrected field.
