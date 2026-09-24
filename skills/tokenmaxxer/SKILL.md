---
name: tokenmaxxer
description: Serious engineering work behind a reviewed plan and adversarial review gates. The required first argument word picks the mode - `build`, `refactor`, `sweep`, or `experiment`. Invoke explicitly, e.g. `/tokenmaxxer refactor <component>`.
argument-hint: "build <task>  |  refactor <component>  |  sweep <area>  |  experiment <goal>"
compatibility: "requires an external review tool — nitpicker, codex, or opencode, resolved by the second-opinion skill; sweep additionally needs the gh CLI and a git repo with a remote; experiment additionally needs a runnable eval command in the target repo"
---

Serious work mode. Task: $ARGUMENTS

## Mode dispatch

The first word of `$ARGUMENTS` is the mode — required, never guessed, never part of the task. If it is not exactly one of the four below, say the keyword is required and ask which one. The keyword is a safety property: `sweep` opens PRs while the user is asleep, so it must never be reached by inference.

- **`build <task>`** and **`refactor <component>`** → `references/attended.md`. Attended: the user is present, approves the plan, and settles the key decisions. `refactor` is build plus a behavior-preservation profile for one accreted component; a codebase-wide rename or pattern migration is `build`.
- **`sweep <area>`** → `references/sweep.md`. Unattended overnight cleanup shipping draft PRs. Never asks once launched; the named area, fixed at launch, is its consent boundary.
- **`experiment <goal>`** → `references/experiment.md`. Metric-driven experimentation. Attended at the ends; autonomous mid-batch strictly under the approved hypothesis tree.

Load only your mode's file and never blend two modes' policies: attended modes pause and ask; sweep never does; experiment asks only at the ends. (The former `followup` mode is retired — recorded follow-ups are worked as ordinary `build` tasks.)

## REVIEW — the cross-review primitive

`REVIEW(target, reviewer)` — resolve the reviewer once at launch via `skill: second-opinion` — its `get_reviewer.sh <repo>` picks the first available of `nitpicker`, `codex`, `opencode` and prints its invocation contract — follow it for every gate. An explicit user choice overrides the pick (pass it as the second argument). Then:

1. Run the external reviewer on the target, adversarially: find the strongest reason this should not proceed, not reasons it is probably fine.
2. Triage each finding, noting what you skip and why: **blocker / P1** (wrong behavior, data loss, security, race, silently swallowed error) — fix always; **major / P2** (maintainability or missing behavior coverage beyond one local spot) — fix this round; **minor / P3** (local naming, style, structure) — fix only if already touching that code; **cosmetic** — skip. Skipped minors and cosmetics die with the round — at most one summary line, never a follow-up block.
3. Repeat, max 5 rounds. A round yielding nothing actionable ends the loop. An open P1 always buys another round, and one still open at the cap keeps the gate closed until the mode's approver rules. Open P2s permit stopping — when another round has stopped earning its cost — but stopping is not a verdict on them: each is surfaced to the approver with a reason, never silently dropped.

The reviewer is external and independent — that is the entire point. Never degrade to self-review: if the reviewer is unavailable, stop and surface it (attended: ask the user to fix it; sweep: abort per its preflight; experiment mid-batch: stop the batch and report — a metric alone is not a gate). There are no internal gates on top — do not add subagent self-review rounds after the external one. Sweep fixes its reviewer at launch and experiment at plan approval — neither swaps mid-run.

Every REVIEW prompt asks for concrete file/line findings across these lenses:

- correctness, security, performance, data loss, races, partial failure;
- scope creep: unrelated changes, hidden behavior changes, extra features;
- overengineering: pass-through wrappers, single-implementation interfaces, layer-cake delegation, future-proof hooks, fallback paths that hide errors. The posture the code moves toward: boring and explicit beats clever; closed sets as enums/newtypes rather than strings and bools (without growing footprint for type ceremony); validate at boundaries and convert to domain types early, no swallowed errors; abstractions pay rent immediately; minimal public surface, zero dead code;
- tests: missing behavior coverage, untested error paths, mocks or monkeypatches of the system under test's own internals, assertions that pin prose or wording rather than behavior;
- project fit: naming, error handling, logging, structure match the existing codebase and CLAUDE.md.

## Triage before fixes

A bug-shaped task (failure, regression, flake, incident, unexplained behavior) gets evidence before theory: exact symptom → strongest available evidence (reproduction, logs, tests, git history) → smallest reliable reproduction → mechanism with file:line → root cause. No fix before the mechanism is established. Prefer observed evidence over code reading, code over history, history over docs, docs over memory; when a signal source is unavailable, say so — never invent ground truth. Use `skill: investigate` when it is installed and the triage needs deep or remote signals.

## Deletion evidence

Nothing is deleted on a plausibility argument. Dead means: a callers search from the repository root covering tests, generated code, and string-name references (DI registries, serialized configs, migrations); a config-value search across environments; for migration-shaped candidates (v1/v2 pairs, compatibility shims, never-set flags) additionally git history — recent commits touching the item mean an in-flight migration, not dead weight; a "no traffic" claim cites a rollout/config source or telemetry, not a static search. Whatever looks dead but cannot be proven dead is a Chesterton's fence: listed for the user, never silently deleted.

## Working doc

One doc per run at `/tmp/tokenmaxxer-<repo-basename>-<mode>-<slug>-<YYYYMMDD-HHMM>.md`. Find an existing doc by globbing `/tmp/tokenmaxxer-<repo-basename>-*` — never guess the name; never overwrite one (append `-2` on a collision). Two parts, two disciplines.

**State** — the top of the doc: the human-readable plan and high-level overview, kept current by editing in place and deleting superseded content. Exactly these sections, never more — a mode's own records (sweep's report buckets and cluster contracts, experiment's ledger) are subsections of the fitting one:

```
# <mode> run — <slug>
base: <sha> · branch: <name> · scope: <...> · status: <...>
## Intent        — the approved contract: goal, inputs/outputs, acceptance criteria, scope boundaries
## Decisions     — one line per settled decision: what was chosen and why
## Tasks         — the checklist, [ ]/[x]
## Gates         — one line per REVIEW round: target, verdict, unresolved count
## Follow-ups    — admitted blocks only (below)
## Outcome       — what shipped, what didn't, where follow-ups went
```

No transcripts, superseded drafts, exploration dumps, or process narration in State — that lives below.

**Log** — everything under a `## Log` heading at the bottom: an append-only journal, one timestamped entry per event — a review round with its findings and their fates, a commit, a decision as it happened, an escalation, a blocker. This is the run's recovery record: write what a cold restart of the run would need, with as much detail as that takes, here and nowhere else.

On resume (compaction, crash, new session): rebuild from State, then scan the Log tail. State outranks memory and the Log — an event isn't done until State reflects it. Build's trivial fast path opens no doc.

## Follow-up blocks

A follow-up block is an admission the discussion missed something; the target volume is zero. Record one only when **all four** hold:

1. **verified** — the defect is confirmed and its mechanism known, not speculated;
2. **outside current authority** — acting on it needs a decision the approver owns (scope, behavior, contract, security);
3. **material** — blocker or major; "chose not to touch it" does not qualify;
4. **actionable now** — answering the question selects a concrete next action; "revisit if evidence appears" fails.

Anything failing the test dies with its review round or gets one summary line. A trade-off created by the current diff never becomes a block — it is resolved before that diff gate closes.

```
- sweep-key: <normalized-path>:<line-range>:<mechanism-slug>
  tier: blocker | major
  defect: <one line, with file:line>
  question: <the decision, answerable without re-reading the codebase, with a recommendation>
  status: open | done (<where it went>) | declined (<reason>)
```

## Escalation

When implementation proves the approved scope, externally observable behavior, an API or data contract, or the acceptance criteria must change: stop and route it to the mode's approver — attended: a focused discussion with the user (`attended.md`); sweep: a *needs-your-call* entry in the run doc; experiment: a parked next-batch proposal. Never smuggle a contract change into a local fix.

---

Hold your own work to the REVIEW lenses — don't wait for review to catch what you can catch yourself. Temporary files go in /tmp.
