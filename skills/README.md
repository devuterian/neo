# Repository skills

`skills/` stores reusable repository-development procedures. Skills describe how to perform a workflow; repository-wide policy remains in [`records/REPO.md`](../records/REPO.md), durable system truth remains in [`records/SPEC.md`](../records/SPEC.md), and runtime procedures remain in [`protocols/`](../protocols/).

Agents should read the relevant workflow even when their runtime does not auto-load repository skills.

Read the relevant `SKILL.md` when a task matches one of these workflows:

- [`repo-orchestrator/`](repo-orchestrator/): route repository work to the correct durable artifact or execution surface.
- [`upstream-intake/`](upstream-intake/): review `LPFchan/repo-template` changes against local contracts.
- [`clean-correction-gate/`](clean-correction-gate/): protect sensitive durable artifacts from ambiguous destructive replacement.
- [`sharpen-the-tip/`](sharpen-the-tip/): iteratively refine substantial plans, specifications, ADRs, and policy documents.

## Local exclusions

This repository intentionally does not adopt:

- commit-generator workflows;
- `LOG-*` commit identifiers;
- prepare-commit or commit-msg hooks;
- prototype-mode compatibility shortcuts;
- daily inbox pressure review before repository capture volume justifies it.

Skills must not instruct agents to read live personal operational data during repository-development work. They must preserve the mode and privacy boundaries in root [`AGENTS.md`](../AGENTS.md).
