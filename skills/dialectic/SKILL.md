---
name: dialectic
description: Prove and counter-prove a claim with parallel agents before concluding. Use for architecture claims, bug hypotheses, performance claims, refactor safety, review judgments, and "is this actually true?" questions.
argument-hint: "<claim>"
compatibility: "the second-opinion skill (nitpicker, codex, or opencode) is recommended"
---

Run a dialectic check on: $ARGUMENTS

The goal is to reduce confirmation bias, not to generate debate theater.

Proportionality: if a single command or test can decide the claim, run it and skip the parallel agents entirely; report the evidence in the same output format.

## Workflow

1. Restate the claim in one precise sentence. If the claim is vague, narrow it before launching agents; if narrowing changes the claim's meaning, confirm the restatement with the user first.
2. Launch two read-only reviewers in parallel, in a single message. Each reviewer prompt must state "investigate only; do not modify the working tree". Prefer one reviewer from a different model/tool for independence, via `skill: second-opinion` when available, usually as Antithesis. If no independent reviewer is available, use two separate subagents with opposing prompts:
   - **Thesis**: find the strongest evidence that the claim is true.
   - **Antithesis**: find the strongest evidence that the claim is false, risky, or incomplete.
3. Require concrete evidence: file paths, line numbers, failing/passing command output, data, logs, or docs. Agents must say when evidence is missing.
4. Verify the important cited evidence yourself by reading the referenced code or output. Do not trust agent summaries blindly.
5. Synthesize the result as one of: **true**, **false**, **mixed**, or **unknown**.
6. If the result affects implementation, state the smallest next action: proceed, change design, add a test/experiment, or ask the user.

## Output

Use this structure:

```markdown
**Claim:** ...

**Thesis evidence:**
- ...

**Antithesis evidence:**
- ...

**Verified conclusion:** true | false | mixed | unknown

**Next action:** ...
```

## Rules

- Evidence beats symmetry. Do not split the difference when one side has stronger proof.
- Prefer one strong finding over many weak guesses.
- Mark speculation as speculation.
- If evidence conflicts, propose the smallest test or experiment that would decide it.
- Do not implement changes inside the dialectic unless the user already asked for implementation and the conclusion clearly supports it.
