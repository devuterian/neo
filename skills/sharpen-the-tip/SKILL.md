---
name: sharpen-the-tip
description: Refine substantial repository plans, specifications, ADRs, and policy documents through focused review cycles.
argument-hint: Draft artifact, goal, constraints, and review focus
---

# Sharpen the tip

Use this skill for substantial plans, specifications, ADRs, migration proposals, repository policy, or operator-facing procedures. Do not use it for trivial edits.

## Output

- a clearer artifact with one explicit purpose;
- the highest-impact issues resolved before cosmetic polishing;
- preserved local contracts and authority boundaries;
- a concise record of unresolved risks.

## Procedure

1. Define the tip.
   - State the artifact's decision or outcome in one sentence.
   - Identify the audience and the action they should be able to take.
   - List non-negotiable local contracts from `AGENTS.md`, `records/REPO.md`, `records/SPEC.md`, and relevant ADRs.

2. Produce or read the draft.
   - Keep facts, decisions, current status, and future plans distinct.
   - Prefer links to canonical documents over duplicated policy.
   - Exclude live personal records, credentials, raw transcripts, and unrelated execution history.

3. Run a neutral review pass.
   - Check scope: does every section serve the stated outcome?
   - Check authority: does the draft create a duplicate source of truth?
   - Check compatibility: are CLI, data, Calendar, privacy, and approval contracts preserved?
   - Check operability: are inputs, outputs, stop conditions, and verification explicit?
   - Check evidence: are claims confirmed or clearly marked as recommendations?

4. Rank findings.
   - **Blocker**: unsafe, contradictory, impossible, or contract-breaking.
   - **Material**: likely to cause wrong implementation or operator confusion.
   - **Minor**: wording, organization, or polish.
   - Address blockers and material findings first.

5. Revise once.
   - Make the smallest coherent revision that resolves the important findings.
   - Do not broaden the artifact to solve adjacent problems.

6. Run one final review pass.
   - Stop after two review cycles unless a blocker remains.
   - Record remaining uncertainty instead of endlessly polishing.

7. Prepare delivery.
   - Confirm links and canonical destinations.
   - Add changelog text when policy or operator behavior changes.
   - List verification actually performed.
   - Keep implementation in a focused follow-up PR when the artifact is only a plan or decision.

## Stop conditions

Stop and request judgment when:

- two local contracts conflict;
- the artifact would change privacy or approval boundaries;
- a migration or compatibility break lacks an accepted decision;
- confirmed facts cannot be separated from speculation;
- review requires opening live personal records during repository-development work.

## Quality bar

- one clear purpose;
- high-impact issues first;
- no duplicated authority;
- no unbounded review loop;
- explicit unresolved risks;
- concise, implementable outcome.
