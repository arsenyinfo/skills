# Harness loop

The loop is the control plane. The model proposes; the harness disposes — one step at a time, under budget, with every action validated, gated, executed, and recorded before the next. Get the loop wrong and the agent spins forever, stops early, or fires a side effect nobody approved. This file owns the loop, the model/harness split, the state machine, the budgets, the subagent patterns, and the improvement loop that turns failures into features.

## The core loop

Spell every step out. Do not hide them inside a black-box runtime — each is a place a bug or an unauthorized action can enter.

```
        ┌───────────────────────────────────────────────┐
        v                                                │
 [1] build context  ── stable first, volatile last       │
 [2] model call     ── returns final answer or tool calls │
 [3] parse action   ── extract calls; reject malformed    │
 [4] validate schema ── types, required, ranges           │
 [5] classify risk  ── read / write / comms / destructive │
 [6] permission gate ── allowed? else deny (still a result)│
       │                                                  │
       ├── high-risk ─> pause for approval ──> denied ────┤
       │                                                  │
 [7] execute        ── retries/timeouts, capture output    │
 [8] normalize obs  ── success/partial/blocked/failed      │
 [9] record trace   ── inputs, decision, result, ids       │
 [10] stop? ──no──────────────────────────────────────────┘
        │yes
        v
   finalize + summary
```

1. **Build context.** System instructions, loaded skills, history, working memory, retrieved content into one payload. Stable content first (cache-friendly), volatile last.
2. **Model call.** Send context plus the tool catalog. Back comes a final answer or one-plus tool calls.
3. **Parse proposed action.** Extract calls, check JSON structure. Malformed calls never reach the tool layer — they return a validation observation.
4. **Validate schema.** Every argument against the tool's schema: missing required, wrong type, out of range. Reject deterministically.
5. **Classify risk.** Map the call to its risk class from the tool's declared side effect, not from the model's say-so.
6. **Permission gate.** The permission engine decides for this user/task/session. A denial is an observation, not a crash.
7. **Execute or pause.** Low-risk runs now. High-risk pauses for approval; on denial the loop still emits a result. Independent calls run concurrently; dependent calls serialize.
8. **Normalize observation.** Raw output becomes a structured result: status, evidence, what to do next, whether retry helps. Redact secrets.
9. **Record trace.** Inputs, risk decision, permission decision, result, trace id — enough to debug without exposing hidden reasoning.
10. **Repeat or stop.** Check stopping conditions at the *end* of the iteration — a mid-turn result can satisfy a done condition. Then loop or finalize.

## Model vs harness — two lists, no overlap

**The model owns judgment:**
- Interpret intent from an ambiguous request.
- Choose among the *valid* actions the harness exposes.
- Synthesize — write the code, the message, the plan, the summary.
- Ask for missing detail before a high-risk action, rather than guessing it.
- Recover from informative observations — read a structured error and change approach.

**The harness owns everything deterministic:**
- Enforce schemas and reject malformed or out-of-range calls.
- Classify risk and check permissions.
- Execute — run the tool, manage concurrency, retries, timeouts.
- Manage state and validate transitions.
- Log traces and run evals.
- Return stable observations, including on failure.

If a responsibility can be made deterministic, it belongs on the right. Safety that matters lives in code, never in a prompt line asking the model to be careful.

## Explicit state / FSM for multi-step flows

Anything multi-step needs an explicit machine. The model may *request* a transition; deterministic code decides whether it happens. Invalid transitions are rejected by the harness, not by the model's goodwill.

Worked example — a change that ships to production:

```
draft ─> scaffolded ─> validated ─> prepared ─> approved ─> committed ─> verified
```

- `draft → scaffolded`: emit boilerplate from a manifest.
- `scaffolded → validated`: schema/lint/type checks pass.
- `validated → prepared`: build the reviewable artifact (diff, migration preview).
- `prepared → approved`: an approval gate clears — the only edge a human or policy can hold.
- `approved → committed`: perform the side effect. Cannot fire from any state but `approved`.
- `committed → verified`: post-conditions checked (tests green, health check passes).

A transition request returns a structured verdict:

```json
{
  "previous_state": "validated",
  "requested_transition": "commit",
  "new_state": "validated",
  "checks_passed": ["schema", "lint"],
  "checks_failed": ["not_approved: current state is 'validated', 'commit' requires 'approved'"],
  "next_allowed_actions": ["prepare"]
}
```

The model asked to skip straight to commit; the machine refused and told it the only door that opens next. No prompt wording can talk past this — the edge simply does not exist in code.

## Budgets, retries, stopping conditions

Every loop is bounded three ways: a **step budget** (max iterations), a **token/time budget** (cost and wall-clock ceilings), and **max retries** per call. Sane defaults: 10–15 steps for a fix, 30–50 for a refactor, ~100 for deep investigation; time-based limits for continuous work. The model does not get to negotiate for more — the harness enforces the ceiling.

**Every tool call MUST receive a result.** Denied, timed out, aborted, budget-cut — the loop still returns a structured observation. The model is part of the error-handling loop; a swallowed failure is a silent lie. Distinguish transient errors (timeout, 429, 5xx → retry with backoff) from permanent ones (4xx except 429, schema violation, permission denied → return immediately). Never auto-retry a non-idempotent write unless the harness can verify the first attempt did not land.

**Stop when any holds:** measurable done condition met · model returns a final answer with no tool calls · step budget exhausted · cost/time budget exceeded · user interrupt · unrecoverable error · refusal (a safety feature — log it, stop, don't re-prompt a reworded version). On every stop, emit a summary of what got done, what remains, and what decision the user owes. Never leave silence.

Long-running goals need a **measurable done condition** and **checkpoints**: `latency_p99 < 200ms`, `coverage > 80%` — not "make it better". Without a metric and a budget, a goal loop is an expensive infinite loop.

## The improvement loop

This is how a harness gets better, and it is a code loop, not a prompt loop. Its input is trajectory analysis — whole traces read end-to-end and failure modes ranked by frequency × cost (see [evals-and-observability](evals-and-observability.md)); aggregate metrics only tell you *that* something broke:

```
agent fails or slows
  → identify the missing piece: capability? context? validator? permission?
  → encode the fix where it belongs: a tool, a validator, a doc, an eval, a policy
     (NOT one more sentence of prompt advice)
  → rerun the failing case and measure
  → keep the improvement; it is now part of the harness
```

When the agent guesses a path, add a scaffold tool that emits it. When it repeats a bad call shape, tighten the schema or the structured error. When it takes a fragile action twice, add a draft/commit split or a permission gate. **Repeated failures become harness features.** A prompt that accretes edge-case advice is a symptom; each accreted line is a validator, tool, or policy that was never written. Measure the fix against the case that motivated it, then keep it as a regression eval.

## Multi-agent — shape the data graph, not an org chart

A single loop that hasn't failed measurable evals doesn't need teammates. When you do split, the test is simple: **a subagent earns its place by changing the shape of the data flow, never by wearing a job title.** "Architect agent, coder agent, QA agent" draws boundaries along human roles, so every agent needs most of the same context and the split buys coordination overhead instead of capacity. The splits that pay follow the data:

- **Map-reduce over many artifacts.** One agent per data unit — a trajectory, a file set, a failure cluster — reads its unit *in full* inside its own context and returns a compact, length-capped, structured summary. Deterministic code aggregates (counts, ordering, dedup); one reduce agent synthesizes from the summaries, never from the raw artifacts. Persist map outputs before reduce starts, and let one map failure drop that unit, not the run.
- **Context isolation for bulk reads.** A subagent is a firewall around a noisy investigation: delegate a bounded question that takes several tool calls ("trace this call path", "survey these files"), and only the conclusion returns — the file dumps die with the subagent's context. Don't delegate what one tool call answers; the ceremony costs more than it saves.
- **Independent verdicts.** Parallel reviewers with distinct lenses and diverse models, aggregated with dissent preserved — the multi-reviewer pattern in [audit-playbook](audit-playbook.md). The value is statistical independence, not division of labor.

Subagents are still agents in your harness: same permission gates, a shared concurrency cap and budget, a depth limit (subagents spawning subagents spawning subagents is runaway, not architecture), and structured outputs back to the parent. The smell test: if every agent became a function call, would the decomposition still make sense? Data-shaped splits survive that question; job titles don't.

## Maturity levels 0–5

Move up only when evidence shows the level below is insufficient — and the evidence bar scales with what the next level can do to the world: a few re-runnable cases to leave Level 1, pass^k on task-grounded, state-verified cases before Level 4.

- **0 — Answer-only.** No tool execution. Q&A, drafting, summarization. Evidence to leave: task-grounded output quality that a downstream step can consume.
- **1 — Retrieval.** Search and read trusted resources; no side effects. Evidence: retrieval precision and grounding — it cites what it read and does not hallucinate sources.
- **2 — Drafting.** Proposes actions, drafts messages, produces plans — no commit. Evidence: proposals a reviewer accepts without heavy rewrite; draft/commit split exists for anything risky.
- **3 — Approval-gated.** Prepares actions, executes only after explicit approval. Evidence: the gate provably holds — no path reaches a side effect without passing it; approvals are legible.
- **4 — Policy-bounded autonomous.** Executes low-risk actions inside strict scopes, budgets, and audits. Evidence: pass^k reliability on the autonomous action set, clean traces, and a demonstrated blast-radius bound.
- **5 — Long-running goal worker.** Continues across sessions toward a measurable objective. Evidence: stable checkpointing, a metric that provably converges, and recovery from interruption without losing approval or plan state.

**Default to the lowest level that does the job.** Levels 4–5 are earned with eval evidence, never chosen at design time.
