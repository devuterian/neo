---
name: clean-correction-gate
description: Gate ambiguous destructive edits to sensitive durable repository artifacts.
argument-hint: Sensitive target artifact and proposed replacement
---

# Clean correction gate

Use this skill for destructive edits to sensitive durable artifacts when the replacement intent is ambiguous or not already explicitly authorized.

This is a narrow local adaptation. It is not a requirement to ask again before every ordinary code or documentation edit.

## Sensitive targets

Apply the gate to destructive replacement of:

- root `AGENTS.md` mode, privacy, approval, or write boundaries;
- `records/REPO.md` and `records/SPEC.md` authority or data contracts;
- accepted ADRs;
- schemas and migration contracts;
- runtime protocols;
- privacy, security, approval, credential, or external-publication policy;
- CI policy that protects live operational data;
- deletion or relocation of a canonical document surface.

## Do not gate again when

- the operator explicitly approved the exact replacement or a clearly bounded implementation plan;
- the edit is additive and does not replace existing policy;
- the change is an ordinary implementation detail inside an already approved PR scope;
- the edit fixes an unambiguous typo or broken link without changing meaning.

## Procedure

1. Read the current target.
   - Read only the relevant section when possible.
   - Do not open live personal records as part of repository-development work.

2. Classify the change.
   - **Additive**: new file, new section, or append-only clarification that does not displace policy.
   - **Destructive**: deletion, relocation, full rewrite, or semantic replacement of existing durable policy.

3. Check authorization.
   - If the exact destructive change is already explicitly authorized, proceed and preserve the approved scope.
   - If the replacement remains ambiguous, present a compact before/after gate.

4. Use this gate shape.

```text
[path] — replacing current policy:
"""
[relevant existing excerpt]
"""

with:
"""
[proposed replacement]
"""

continue? yes / no / show full diff
```

5. Write cleanly after approval.
   - The artifact contains only the final intended policy.
   - Do not preserve conversational correction history such as “not B” or “as corrected”.
   - Put rationale in the PR or ADR when it is durable and relevant.

6. Verify authority and links.
   - Ensure the replacement does not create a duplicate canonical surface.
   - Update references and changelog when operator workflow or policy changes.

## Escalate when

- the target boundary is unclear;
- several sensitive artifacts would change but their authority order is uncertain;
- the proposed replacement weakens privacy, approval, or live-data protection;
- the edit changes runtime behavior but is presented as documentation-only;
- the user’s authorization does not cover the destructive consequence.

## Quality bar

- no unnecessary confirmation loops;
- literal and compact gate when needed;
- final artifact free of correction-history debris;
- explicit authorization for genuinely ambiguous sensitive replacement;
- no live personal-data access during repository-development work.
