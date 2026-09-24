# Tool design

A tool is a contract, not a function. The model reads that contract — name, purpose, typed input schema, output schema, declared side-effect class, risk class — and decides what to call. The harness owns everything the model can't see: validation, execution, permission checks, logging. Design each tool so the model can pick it, fill it, and read its result without guessing. Everything below is how you make that contract unambiguous.

The illustrative JSON in this file is design guidance, not a required wire format — copy the shape, not the field names, into whatever your platform speaks.

## The contract, minimally

Every tool declares, in your harness, at least: name, one-line purpose, input schema, output schema, side-effect class, risk class, resource scope, timeout, result-size cap, retry policy, error format. The model is shown only name + description + input schema; the rest the harness enforces. If a field is load-bearing for safety, it lives in the harness, never in prose the model can talk its way around.

## Non-collapsing names

One verb, one meaning. The agent must never stall deciding between `get_file`, `fetch_file`, and `download_file` — that hesitation is a design defect that surfaces as a wrong call under load.

- Bad group: `get_file`, `fetch_file`, `download_file`, `load_file`, `read_data` — four names, one concept, guaranteed misfires.
- Better group: `repo.read_file(path)` for a local repo read, `net.download_asset(url, dest)` for a remote fetch. Two names, two distinct concepts, no overlap.

Verb-first, spelled out, no abbreviations (`calculate_total`, not `calc_total`). Pick one verb per action and hold it everywhere: `read_*` retrieve, `search_*` query, `create_*`/`update_*`/`delete_*` mutate, `draft_*` propose, `send_*`/`apply_*` commit, `validate_*` check, `scaffold_*` generate. If reads are `read_*`, never introduce `fetch_*` later — consistency beats the "perfect" verb.

Namespace by service and resource once scopes collide: `repo.search`, `repo.read_file`, `deploy.prepare`, `deploy.commit`. The prefix carries the boundary so `read(id)` doesn't mean three different things. (Prefix-vs-suffix has measurable, model-dependent selection effects — pick based on your evals, not taste.)

Mind the provider boundary: native OpenAI/Anthropic function names must match `[A-Za-z0-9_-]{1,64}` — **no dots**. The dotted forms here are a readable convention for your internal registry; on the wire, sanitize deterministically (`repo.search` → `repo__search` — `__` is a common flattened-namespace separator) and keep the mapping one-to-one so the namespace survives. Raw MCP tolerates `.`; the model-facing surface a provider exposes often does not.

Reject overloaded verbs outright: `execute`, `run`, `do`, `manage`, `process`, `handle`. A tool named `manage_users` has no contract — it's a freeform instruction slot wearing a schema. Decompose it.

## Descriptions are engineered contracts

Write the description the way you'd brief a new hire on their first day: what it does, when to reach for it, when *not* to, what side effects fire, what the result means. Two to four sentences. Name the prerequisite ("read first to get an `id`") and the follow-up.

Do not overspecify to every past failure. Enumerating every error that ever happened, every edge case, every internal branch is overfitting — the description rots the moment the implementation shifts. If a behavior is load-bearing, it does not belong in prose: push it into the schema (an `enum`, a `required` field), a validator, or a structured error the model can read and act on. Prose steers; code enforces.

Bad: `get_stuff: Gets stuff from the system.` — no when, no not-when, no result semantics. `file_tool: reads and writes and can delete too` — no boundary, so every file op collapses onto it.

## Parameters

Explicit, typed, minimal, hard to confuse, named after user-visible concepts. `user_id`, not `user`. `record_id`, not `record` (which invites a name, a query, or a paragraph). Use `enum` for every small closed set instead of an open string — the model can't fill an illegal value it was never shown. Mark `required` honestly and set `additionalProperties: false` so a hallucinated extra field is rejected, not silently swallowed.

Poka-yoke the arguments — design the parameter so a whole error class becomes unrepresentable. Requiring absolute paths kills every relative-path ambiguity at once. Taking a typed `approval_id` instead of re-passing the original amount kills tampering between draft and commit. Prefer IDs over free references so the agent reads first, then acts on the handle — a two-step pattern that is trivial to validate and audit.

## Few high-leverage tools, not thin wrappers

More tools is an anti-pattern. A registry of tools that each mirror one API endpoint pushes all the orchestration into the model's context, where it's slow and unreliable. Build a few workflow-shaped tools that do the thing the user actually wants:

- `schedule_event(attendees, window)` over making the model chain `list_users` + `list_events` + `create_event`.
- `search_contacts(query)` over `list_contacts()` that dumps the whole address book into context.
- `get_customer_context(id)` over `get_customer` + `list_transactions` + `list_notes`.

Prefer `search_*` to any `list_*` that returns the world. The tool that consolidates a known multi-call chain saves context and removes the join the model would otherwise get wrong.

This is the Unix ethos sized for agents: each tool does one thing well, with simple typed params, and composes cleanly — but the "one thing" is a user-meaningful task, not an API endpoint. Splitting by endpoint fragments a task across calls; lumping tasks behind one verb collapses meaning. Same defect either way: the tool boundary drawn somewhere other than the job.

## Bounded output

Never stream unbounded data into the model. Every tool that can return a lot takes `limit` / `cursor` / `max_bytes` / `include_body` and enforces a default cap — treat ~25k tokens as the sane ceiling for a single response. When you truncate, say so: a `truncated: true` / `has_more` flag plus a cursor to continue, so the model knows the view is partial and how to page. For large artifacts (test runs, log dumps, exports), return a summary plus an `artifact_id` reference, not the payload.

Return semantic fields, not machine plumbing. `{"name": "invoice.pdf", "file_type": "pdf"}` beats `{"uuid": "...", "mime_type": "application/pdf"}` — resolving raw UUIDs and mime types to natural-language, human-meaningful fields measurably cuts hallucination and lets the model reason about what it got.

## The result envelope

This is the center of the whole design. **Every result is the next observation** — the sole thing the model sees before its next move. A result that doesn't tell the model what happened and what to do next forces a guess. Adopt one standard shape across every tool:

```
{ status: "success" | "partial" | "blocked" | "failed",
  summary, details, evidence, next_actions,
  retryable, error_code, suggested_fix }
```

Success — say what happened and what's now valid:

```json
{ "status": "success",
  "summary": "Found 3 cases matching 'login timeout'.",
  "details": { "count": 3, "items": [{ "id": "case_101", "title": "Login timeout on mobile" }] },
  "next_actions": ["read_case", "draft_response"] }
```

Error — a stable machine-readable `error_code`, the exact failing input, a fix, and how to verify it:

```json
{ "status": "failed", "error_code": "not_found",
  "summary": "No customer for email 'user@example.com'.",
  "evidence": { "queried_email": "user@example.com" },
  "retryable": false,
  "suggested_fix": "Search by name via customer_search, or create_customer_record.",
  "next_actions": ["customer_search", "create_customer_record"] }
```

Blocked — the action is real but gated on approval, so the model routes to the draft/commit path instead of retrying blindly:

```json
{ "status": "blocked", "error_code": "approval_required",
  "summary": "Sending external email requires approval.",
  "retryable": false,
  "suggested_fix": "Call draft_email to prepare it, then request_approval.",
  "next_actions": ["draft_email", "request_approval"] }
```

Contrast the anti-pattern: `Error: failed`. It carries no code to branch on, no failing input, no fix, no next step — the model can only retry the same call or hallucinate a workaround. Write Rust errors, not C++ errors: the failing input, the reason, and the exact next step — not an opaque dump the reader must decode. Keep `error_code` values stable and finite (`invalid_arguments`, `not_found`, `permission_denied`, `approval_required`, `conflict`, `timeout`, `rate_limited`, `non_idempotent_retry_blocked`) so the model — and your evals — can match on them.

The draft/commit split that produces the blocked case is a risk concern, covered in [permissions-and-risk.md](permissions-and-risk.md); the tool-design duty here is only that the envelope routes the model there cleanly.

## Tool visibility

Selection accuracy degrades as the surface grows — past roughly 15–20 concurrently visible tools the model starts picking wrong (field reports put the first cracks as low as ~10). Don't expose the whole registry at once. Reveal subsets per task: a base set always on, task-scoped tools after you classify the request ("run the tests" surfaces `run_tests` and hides `deploy_service`), connector tools after auth, sensitive tools only when needed and approved. Implement this in the harness, never by hoping the model ignores irrelevant entries.

## Before you add a tool

- Does it need to be a tool at all, or is it deterministic work that belongs in a script?
- Is the name unambiguous — one verb, one meaning, no collision with an existing tool?
- Is it too broad? Does it overlap something already in the registry (merge, rename, or wrap instead)?
- Are the side effects and risk class obvious from the contract?
- Is the schema restrictive — typed, `required` honest, enums for closed sets, `additionalProperties: false`?
- Is output bounded and are results structured (envelope, not prose)?
- Are errors actionable — stable `error_code`, failing input, `suggested_fix`, `next_actions`?
- Does an eval case exist that exercises it?
