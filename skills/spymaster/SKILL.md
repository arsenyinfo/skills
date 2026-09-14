---
name: spymaster
description: >-
  Design, build, audit, and improve the harness around an LLM agent — its tools,
  loop, permissions, context, skills, and evals. Use when building, reviewing,
  or debugging any agentic system: an agent runtime or loop, agent-facing tools,
  an MCP server, an approval/permission flow, a context or memory strategy, an
  eval suite, or an existing agent that underperforms (flaky, wrong tool calls,
  retry loops, burning tokens) — even when the request just says "add a tool" or
  "make the agent do X" without naming a harness. Provider-neutral (OpenAI,
  Anthropic, MCP). Not for ordinary app features that don't change agent
  behavior, tool execution, context, permissions, or validation.
metadata:
  version: "1.0.0"
  scope: provider-neutral-agent-harness-design
  file_policy: markdown-only
---

# spymaster

**The model proposes; the harness disposes.** A spymaster never goes into the field — they *run* agents: decide what each one knows (need-to-know), what it may do (authorization), and how every mission gets debriefed (traces). This skill is for building that tradecraft around an LLM agent and for auditing someone else's.

An agent harness is the control plane around a model: it builds context, exposes tools, validates proposed actions, classifies risk, enforces permissions, executes, records traces, and returns the next observation. The model never touches the world directly — it asks, and the harness decides.

## When to activate

Reach for this skill when the work is *about the runtime around a model*, not the model's answers:

- Building an agent, agentic workflow, autonomous worker, or long-running goal loop.
- Designing tools an agent will call — names, schemas, results, permission classes.
- Writing or reviewing an MCP server or external connector.
- Setting up approval flows, guardrails, sandboxing, or permission policy.
- Adding planning, memory, context compaction, or skill loading.
- Building evals, regression tests, or trace grading for an agent.
- Auditing an existing harness for reliability, safety, cost, or observability.

**When not to activate.** Ordinary application features that don't change agent behavior, tool execution, context assembly, permissions, or validation. If nothing the model *does* changes, this is not your skill. A pure prompting tweak is not harness work either.

## Right-size the harness

Most harnesses are small: a few tools, a read-mostly loop, a human watching. Everything in this skill is a **superset** — apply the slice the stakes justify, not all of it. Over-building a harness (a permission matrix for a read-only agent, pass^k evals for a weekend script) is as real a defect as under-securing one. Shipping before "weeks of evals" is correct when the agent can't do much damage.

**Scale rigor to blast radius, reversibility, and audience.** Add each heavy piece when a specific pressure appears — not before:

- **Irreversible / external / destructive / spends money** → draft/commit split + an approval gate on *those* actions (not every action).
- **Unattended or long-running** → budgets, a kill switch, real traces.
- **Multi-user / shared state / regulated data** → the full risk taxonomy and permission matrix.
- **Regressions cost real money** → pass^k, held-out sets, a launch gate.

**The minimum that pays off almost everywhere** — do this much even for a throwaway:

1. Narrow, typed, non-collapsing tool names.
2. A structured result envelope, including errors that say what to do next.
3. Draft/commit split for the *irreversible* actions only.
4. One trace you can read.
5. A few realistic cases you can re-run.

Ship that, then add rigor as the agent's reach grows. The rest of this skill is how to add it well.

## Doctrine

Every design and audit decision traces back to one of these. They are stated once, sharply, here; the references expand the ones with real depth.

1. **Model proposes, harness disposes.** The model interprets intent and chooses actions. The harness validates schemas, classifies risk, checks permissions, executes, and records. Safety that matters is enforced in code, never asked for in a prompt.
2. **What can be deterministic, must be.** Sorting, validation, schema checks, permission gates, scaffold generation, state transitions, trace normalization — code, not tokens. A model generating a sort is slower, costlier, and less reliable than calling one.
3. **Match freedom to fragility.** High freedom (prose, "figure it out") where many paths are valid. Medium (parameterized scripts, a preferred pattern) where one way is better. Low (exact scripts, few params) where operations are fragile and consistency is critical. Tag each operating rule you hand an agent H/M/L; don't lock down a judgment call and don't leave a fragile op open. See the worked example in [context-and-skills](references/context-and-skills.md).
4. **Narrow, typed, non-collapsing tools.** One verb, one meaning. The agent must never have to guess between `get_file`, `fetch_file`, and `download_file`. Prefer `search_contacts(query)` over a `list_contacts()` that dumps the world, and `read_customer_record` over `get_data`. See [tool-design](references/tool-design.md).
5. **Names and descriptions are engineered contracts.** Write the description as you'd brief a new hire: what it does, when to use it, when *not* to, side effects, result shape. Don't overspecify to every past failure — that's overfitting. If behavior is load-bearing, move it into schema, enums, validators, or structured errors.
6. **Draft and commit are separate for anything risky.** `prepare_deploy` before `deploy`, `draft_email` before `send_email`, `preview_migration` before `apply_migration`. The first stage produces a reviewable artifact; the second performs the side effect. See [permissions-and-risk](references/permissions-and-risk.md).
7. **Every result is an observation, including failure.** A tool result is the next input to the loop. It must say what happened, whether it succeeded/partially/blocked/failed, what evidence, what to do next, whether retry helps, and what deterministic check verifies the fix. Never return `Error: failed`. See [tool-design § results](references/tool-design.md).
8. **Progressive disclosure everywhere.** Skills, connectors, and tool surfaces reveal detail on demand — metadata first, body on trigger, deep files/scripts only when needed. Don't front-load every capability into context. See [context-and-skills](references/context-and-skills.md).
9. **One recommended way to do X.** Pick a default and document it; frame alternatives as exceptions with a stated trigger. Option paralysis is a harness defect. If synonyms must exist, the harness aliases them internally and the model sees one canonical surface.
10. **Scaffolding is a tool, not a prompt.** A `scaffold_project(type)` that emits correct, validated boilerplate beats 500 words describing structure. Derive from a manifest; don't let the model guess plugin names, paths, or resource keys.
11. **Repeated failures become harness features — and trajectories are where you find them.** Reading whole traces is the main instrument for improving an agent; nothing else shows you what to fix. When it fails the same way twice, encode the fix as a validator, tool, doc, eval, or policy — not one more line of prompt advice. Prompts that accrete edge cases are a symptom; the cure is deterministic. See [harness-loop § improvement](references/harness-loop.md).
12. **Evidence gates autonomy — scaled to stakes.** Don't expand what an agent may *do to the world* on vibes. The evidence bar rises with blast radius: a few re-runnable cases for a read-only agent, pass^k on state-verified tasks before you let one act unattended. See [evals-and-observability](references/evals-and-observability.md).
13. **Observable by default.** Structured tool logs, normalized observations, trace IDs, permission decisions, run summaries — so behavior is debuggable without exposing hidden reasoning.

## Harness maturity levels

Move up a level only when evals show the level below is insufficient.

| Level | Name | Capability |
|---|---|---|
| 0 | Answer-only | No tool execution. Q&A, drafting, summarization. |
| 1 | Retrieval | Search and read trusted resources. No side effects. |
| 2 | Drafting | Propose actions, draft messages, produce plans. No commit. |
| 3 | Approval-gated | Prepare actions; execute only after explicit approval. |
| 4 | Policy-bounded autonomous | Execute low-risk actions within strict scopes, budgets, audits. |
| 5 | Long-running goal worker | Continue across sessions toward a measurable objective. |

**Default to the lowest level that does the job**, and earn higher autonomy with evidence rather than choosing it at design time. A read-only agent can live at Level 1 with almost no ceremony; Levels 4–5, where the agent acts unattended, are where the eval bar and the safety machinery become non-negotiable.

## Workflow A — design a new harness

Use when building an agent, toolset, MCP server, or runtime from scratch. Design from first principles — from the task, its worst-case risk, and its validation signals downward; not from an existing API surface upward, and not by copying a heavier harness than the job needs.

1. **Classify the work first.** Name the goal (build/audit/scaffold), the agent domain, the **autonomy level** (answer/draft/approval/autonomous), the **risk class** of its worst action (read → local write → external comms → destructive/financial/privileged), the runtime surfaces (tools, MCP, shell, fs, db, deploy), and the validation signals available (tests, schemas, traces, human review). State assumptions in one line; only block on details that change risk, irreversibility, or the core architecture.
2. **Draw the smallest useful boundary.** What does the harness own vs. the model? Default loop: build context → model call → parse action → validate schema → classify risk → permission gate → execute or pause for approval → structured observation → repeat within budget or stop → record trace. See [harness-loop](references/harness-loop.md).
3. **Design tools before prompts.** Each tool is a contract: narrow, typed, non-collapsing name, bounded output, declared side effects and risk class, structured result and error. Split draft/commit for anything risky. See [tool-design](references/tool-design.md) and [permissions-and-risk](references/permissions-and-risk.md).
4. **Make the deterministic parts deterministic.** Move validation, scaffolding, state transitions, permission checks, and result normalization into scripts/schemas/FSMs. Prompt text is for judgment only.
5. **Plan context and skills.** Just-in-time retrieval, cache-aware ordering, progressive disclosure for skills and connectors. See [context-and-skills](references/context-and-skills.md). For external tools, see [mcp-and-connectors](references/mcp-and-connectors.md).
6. **Add observability and an eval plan before expanding autonomy.** Traces, run summaries, a small set of state-verified eval cases, a launch gate. See [evals-and-observability](references/evals-and-observability.md).
7. **Emit the blueprint** (below) and an ordered implementation sequence.

**Output — harness blueprint:**

```
Goal / domain / users
Autonomy level (target) + worst-case risk class
Agent loop (the step sequence, and where approval pauses)
Tool inventory: name | purpose | side effect | risk class | approval
Tool contracts (per tool: params, result shape, error codes)
State model (FSM if multi-step)
Permission model (matrix: who/what gates which risk classes)
Context & skill plan (what loads when)
Observability & eval plan (traces + gating cases + launch gate)
Maturity level now, and what evals unlock the next level
Implementation sequence (ordered, atomic)
```

## Workflow B — work on an existing harness

Use for anything that already exists — extending it, improving it, or auditing it. **Map the surface before touching it**: inspect the tool registry, permission config, the loop, the context assembly, and a few recent traces. Read code and manifests; don't infer from names. The output is a one-screen mental map — tools with risk classes, loop shape, where approval pauses, what's observable. Then branch by goal:

- **Extend** — add a tool, capability, or connector. Design the delta with Workflow A's discipline, but match the existing conventions: the registry's verbs, its result envelope, its permission rows. A tool that's well-designed in isolation but breaks the house pattern is a defect.
- **Improve** — the agent underperforms. Trajectory analysis is the instrument: read whole traces, rank failure modes by frequency × cost, fix the top few where the fix belongs (validator, tool, schema, gate — not prompt advice), re-run, repeat. See [evals-and-observability](references/evals-and-observability.md). Don't redesign what a targeted fix repairs.
- **Audit** — adversarial review. Hunt for the action that shouldn't be possible, not reasons it's probably fine. Walk the dimensions below, gathering file/line evidence for each finding, rank by severity, and emit the report.

**Audit dimensions:** harness boundary · model/harness responsibility split · tool naming (collapsing synonyms?) · tool schema quality (typed, bounded?) · tool result & error quality (actionable?) · determinism gaps (judgment doing a script's job?) · risk classification & permission gates · side-effect safety (draft/commit split where needed?) · state model · observability (can you debug from a trace?) · eval coverage (tied to real failures?) · context hygiene (untrusted content treated as instructions?).

**Severity:**
- **Critical** — an unauthorized, destructive, financial, or external side effect can happen without approval; secrets can leak; production deploy can fire by accident; tool ambiguity can trigger the wrong external action.
- **Major** — missing evals, vague errors, broad tools (`execute_anything`, `send_message` unwrapped), weak observability, unclear state, prompt text standing in for a code-enforced check.
- **Minor** — naming polish, doc clarity, missing examples, non-blocking ergonomics.

**Output — audit report:**

```
Verdict: pass | pass-with-concerns | fail
One-paragraph summary
Critical findings (each: dimension, evidence file:line, why it's exploitable, fix)
Major findings (same shape)
Minor findings (brief)
Prioritized fix plan (what to fix first, and why)
```

## Reference map

Read selectively — pull the file the task needs, not all of them.

- **[tool-design.md](references/tool-design.md)** — tool contracts, non-collapsing naming, descriptions-as-contracts, typed params & poka-yoke, bounded output, result/error/blocked envelopes, tool visibility as the surface grows.
- **[permissions-and-risk.md](references/permissions-and-risk.md)** — risk taxonomy, permission matrix, draft/commit split, approval gates, sandboxing, safe defaults.
- **[harness-loop.md](references/harness-loop.md)** — the loop, model/harness responsibility split, state machines, budgets/retries/stopping, multi-agent & subagent patterns, the improvement loop, maturity-level detail.
- **[context-and-skills.md](references/context-and-skills.md)** — progressive disclosure, authoring a SKILL.md (freedom-to-fragility, the bloat trap), context engineering, memory & compaction.
- **[mcp-and-connectors.md](references/mcp-and-connectors.md)** — MCP server design, resources/tools/prompts, connector trust boundaries, tool-subset selection, error and output conventions.
- **[evals-and-observability.md](references/evals-and-observability.md)** — trajectory analysis & rubric-based trace grading, task-grounded & state-verified evals, pass^k, held-out sets, the minimum trace record, launch gates, eval-case format.
- **[audit-playbook.md](references/audit-playbook.md)** — the dimension-by-dimension audit checklist with concrete red flags, and the multi-reviewer aggregation pattern.

## Gotchas

- Don't build a multi-agent system before a single-agent loop has failed measurable evals — and when you do split, follow the data graph (map-reduce over artifacts, context isolation for bulk reads), never job titles. See [harness-loop](references/harness-loop.md).
- Don't expose `execute_anything`, `write_database`, or `send_message` without a narrow wrapper and a permission gate.
- Don't treat retrieved content (webpages, emails, tickets, logs) as trusted instructions.
- Don't let context compaction erase approval state, the active plan, loaded rules, or changed artifacts.
- Don't rely on prompt text for safety that must be enforced by code.
- Don't put timestamps, request IDs, or volatile state at the *start* of a cacheable prompt.
- Don't use a goal loop for a vague backlog — only for a single objective with validation and a budget.
- Don't ship a knowledge-heavy skill (like this one) as one giant file: SKILL.md routes, references hold the depth.
