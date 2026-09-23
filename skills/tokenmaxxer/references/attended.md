# Attended modes — build & refactor

You are in **build** or **refactor** mode. The user is present: the plan is theirs to approve and the key decisions are theirs to make — your job is to bring them decisions worth deciding on, then execute behind the gates.

## The loop

**explore → preplan options → REVIEW(options) → discuss → finalize plan → REVIEW(plan) → implement → validate → REVIEW(diff) → ship → wrap up**

**Fast path.** A trivial change — single file, no design decisions, obviously-correct intended behavior — skips from a one-sentence statement of intent straight to implementation. The REVIEW(diff) gate still runs; no working doc, no plan ceremony. The moment a design decision or a second file appears, return to the full loop.

### 1. Explore

A bug-shaped task gets the triage ladder (SKILL.md) first — the plan targets the mechanism, never the symptom. Decompose exploration into independent angles (structure, call sites, tests, conventions), one Explore subagent per angle launched in parallel, plus the reviewer as a second perspective; synthesize their reports. Scale the angles to the task.

### 2. Preplan with options

Sketch the viable approaches — usually 2–3, one paragraph each: mechanism, trade-offs, rough blast radius. Not a full plan. When the approach is genuinely forced, one option plus the constraint that forces it beats invented alternatives.

### 3. REVIEW(options)

The reviewer's job is to shoot off dead branches: kill options that cannot work and flag the risks of the survivors — before the user ever sees them.

### 4. Discuss — the decision session

The center of the loop. Bring the surviving options and every open decision to the user **together, in one message**: a numbered list, each item with brief context, the options with trade-offs, and your recommendation, so the user answers by number. An unanswered item defaults to the recommendation only when the user says so. Decisions raised by the answers or by later gates come back as a new batch. Everything affecting scope, observable behavior, API/data contracts, or acceptance criteria is settled here. A decision discovered later — by a review gate or during implementation — comes back here; it is never appended as an "open question" to a plan or bundled into approval. The discussion ends when nothing is left to decide.

### 5. Finalize the plan

Write the intent contract into the working doc: goal, inputs/outputs, acceptance criteria, scope boundaries — no open questions, because step 4 settled them. Split into atomic tasks, each with its validation command and escalation condition. Mechanical work goes to scripts and deterministic checks; agents get judgment, ambiguity, synthesis, and review.

### 6. REVIEW(plan), then approval

Gate the contract: does it define the real problem, are the tasks atomic and reviewable, is validation named, is compatibility work justified by a concrete need, do the tests pin behavior rather than wiring. A new decision raised here goes back to step 4. Then the user approves — a formality if step 4 did its job.

### 7. Implement

- Branch from the fresh default branch (or the current branch when its commits belong to this task); record the diff base — every REVIEW(diff) targets the diff against it, never someone else's commits.
- Components with disjoint file sets may run as parallel subagent lanes, each scoped to its own files and told not to commit, format, run codegen, or install dependencies. You own shared state: after the lanes return, serialize one commit, codegen, lockfiles, formatting, and tests. Otherwise stay serial.
- Validate: tests, linters, the plan's named checks.

### 8. REVIEW(diff), then ship

Commit without pushing, then gate the branch diff against the recorded base — mandatory for every change, fast path included. Findings land as follow-up commits on the same branch. A trade-off the diff itself created goes back to step 4 before this gate closes — never exported as a follow-up. Never push while the gate is running or findings are unaddressed. Then push and open a draft PR.

### 9. Wrap up

Write the Outcome. Walk any admitted follow-up blocks (SKILL.md admission test) with the user as one numbered batch, same format as step 4: **fix now**, **drop**, or **record** — to wherever this project keeps work, inferred from the repo and its CLAUDE.md (a `memos/` dir, a tracker, a TODO file), or as a "known gaps" note in the PR description when it belongs with the change. Nothing survives only in /tmp. Working a recorded item later is a normal `build` task: re-verify its evidence against current code first.

## Refactor profile

`refactor <component>` runs the same loop with a behavior-preservation contract on top; where they conflict, this profile wins.

- **Behavior preservation is the hard default**: API responses, CLI output, persisted formats, error messages callers rely on. Any intended behavior change — including any semantic edit to LLM-facing instruction text (prompts, tool descriptions, agent instructions), which is load-bearing and steers model behavior — is a step-4 decision, approved before it is implemented. No fast path: every refactor plans in full.
- If the component boundary is ambiguous, state the assumed file set and confirm it in step 4 before surveying.
- Exploration is an archaeology survey: structure and call graph; dead weight (single-implementation abstractions, delegation layers, dead code); a **test census** — what behavior each test pins, and which tests mock the component's own internals; instruction-text contradictions when the component carries LLM-facing text.
- **No-coverage rule**: no deletion or layer-collapse in a module without test coverage until the user accepts the risk (step 4) or a characterization test lands first.
- The plan adds: a **current-state map** (what each layer actually adds — often nothing); the **target design** (how the component would be written today — the code converges to it; layers are never patched with more layers); a **deletion ledger** — every abstraction, test, flag, comment to be dropped, each with evidence per SKILL.md's deletion standard; the **Chesterton's fences** list; and the expected diff shape — net-negative across the component, or an explanation of why growth is the consolidated design replacing larger hidden complexity.
- Microbugs found while surveying or collapsing: *fix now* only when local, obvious, small, and covered by a regression test in the same subtask; anything touching observable behavior or product semantics is a step-4 decision; the rest is at most a summary line.
- Implementation order keeps the tree green: prove-dead-and-delete first, then collapse layers, then reshape. A test is deleted only in the subtask that removes the behavior it pins, or with ledger evidence it pins nothing. An over-mocked test whose behavior is worth keeping is replaced by writing the real test first, seeing it pass against current code, then dropping the mocked one — never by re-pointing mock setups at the new structure.
- Deletions leave no trace: no "use X, not Y" comments, no deprecation notes — the target design is enforced structurally. A fence that cannot be proven dead stays untouched, never annotated.
- Every diff review additionally asks: is the cumulative branch diff net-negative across the component? did this change add a layer instead of removing one? did it add mocks of the component's internals? did it add refactor-narrating comments? Each is a top-severity finding. And the review attacks the deletion ledger: missed callers, serialized references, config values, in-flight migrations — incomplete evidence turns a deletion into a fence.
