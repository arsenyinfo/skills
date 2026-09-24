# MCP and connectors

An MCP server is a **capability provider**, not a trust boundary. It hands the model a menu of tools, resources, and prompts over a wire protocol. It does not — and cannot — decide whether the model is allowed to call any of them. That decision stays where it always was: in your harness. Wiring in a server does not import its safety posture; it imports its attack surface.

## The one principle

**An MCP tool is subject to the same risk classification and permission gates as a tool you wrote yourself.** The transport is irrelevant to trust. A `delete_repo` reached over stdio is exactly as destructive as one defined in-process. So:

- Classify every advertised tool by risk (read → local write → external comms → destructive/financial/privileged) at registration time, the same taxonomy you apply to native tools. See [permissions-and-risk.md](permissions-and-risk.md).
- Do **not** trust a tool because it came from an MCP server — not even a first-party one. A server can add, rename, or re-scope tools between calls; re-validate the advertised surface, don't cache trust.
- Treat every tool result as untrusted content, never as instructions. A compromised or hostile server returns text engineered to steer the model. Result text is data. See the SKILL Gotchas.
- The harness owns approval, truncation, redaction, and logging around the call. The server owns only *doing the thing*.

## Naming (matches native tool discipline)

- Names are 1–128 chars, case-sensitive, `[A-Za-z0-9_.-]` only, and unique within a server.
- Aggregators that fan several servers into one surface **should** prefix each name with a server identifier so `github.search` and `gitlab.search` don't collide. Resolve cross-server collisions at the aggregation layer, not by hoping.
- Same non-collapsing-verb rule as native tools: one verb, one meaning, no `get_file`/`fetch_file`/`download_file` triplets. The model must never guess which synonym fires the side effect. See [tool-design.md](tool-design.md).

## Result and output conventions

- **Errors in-band.** Report *tool execution* failures inside the result object via `isError`, not as a protocol-level (JSON-RPC) error. Reserve JSON-RPC errors for protocol faults (unknown method, malformed request); a tool that ran and failed is a result the model must read and recover from, so it belongs in-band as an observation. Every result — success, partial, blocked, failure — is the next input to the loop.
- **Structured output.** Declare an `outputSchema` and return `structuredContent`; also return a text block for backward compatibility with hosts that don't consume structured output. Validate the payload against the schema before returning it, so the model never sees a shape you didn't promise.
- **Semantic fields, bounded size.** Return names, not raw UUIDs; paginate, filter, and truncate with sane defaults rather than dumping. The harness truncates again as a backstop.

## State via explicit handles

The Streamable HTTP transport can carry a transport-level session (an `Mcp-Session-Id`), but **there is no protocol-level guarantee of server-side application state**, and sessions expire and drop. Don't assume the work you did in one tool call is still remembered in the next. Model any multi-step flow explicitly: a creation tool returns a handle (a run ID, a transaction token), and every later tool accepts that handle as a parameter. State the model can see and pass is auditable and replayable; hidden server state is neither. This is the FSM discipline from the harness loop, expressed over a stateless wire.

## Keep the tool count low

Model accuracy degrades noticeably once the exposed surface passes roughly **15–20 tools** (the first cracks show as low as ~10) — wrong tool, wrong params, redundant calls. So:

- Don't advertise everything a server *can* do. Advertise capabilities and let the host **select a subset** for the task at hand (the pattern behind subset-selection headers).
- Consolidate multi-call chains into workflow-shaped tools before adding more. A server with 8 sharp tools beats one with 40 thin wrappers.
- If an aggregator merges many servers, the combined count is what the model pays for. Budget across servers, not per server.

## Present servers as code APIs when the token math demands it

Loading every tool definition into context and round-tripping every intermediate result through the model is expensive at scale. The alternative: expose the MCP servers as a **code API the agent calls inside a code-execution sandbox**. The agent writes a short script that calls the tools, chains them, filters, and returns only the answer — tool schemas load on demand, and intermediate data (the 10k-row query, the full file listing) stays in the sandbox instead of flooding context. Reported token reductions run very large (up to ~98.7% in one Anthropic example). Use it when a task fans across many tools or moves bulky intermediate data; the sandbox boundary is the same one that contains a risky tool, so you get the token win and the isolation together. Skip it for a two-call flow where the ceremony costs more than it saves.

## Server boundaries — the real safety lever

Design **domain-specific** servers: `repo`, `db-migration`, `deploy`, `issue-tracker`, `eval`. A domain server has a bounded, classifiable, wrappable surface. You can reason about its worst action.

Treat these as **high-risk by default** — they collapse straight back into the `execute_anything` anti-pattern the whole skill exists to prevent:

- **General shell servers** (`run_command`, `bash`) — one tool, unbounded blast radius, unclassifiable.
- **Universal API callers** (`http_request`, `call_any_endpoint`) — the model picks the side effect at runtime; you cannot gate what you cannot name.
- **Unrestricted cloud-admin or database servers** (`aws`, `kubectl`, `write_database`) — privileged and destructive behind a single verb.

If you must expose one, wrap it: narrow it to specific commands/endpoints/tables, split draft from commit, and gate every risky path. An unwrapped general server is a Major finding in an audit.

## Transport and security, in brief

- Prefer the current Streamable HTTP transport over deprecated SSE.
- Require auth on HTTP transports (OAuth 2.1); stdio inherits the process's trust boundary — mind what that process can reach.
- Make tool calls **idempotent** with client-generated request IDs so a retry after a dropped response doesn't double-fire a side effect.
- **Version the surface** and advertise capabilities so the host negotiates rather than guesses.

## Connector safety checklist (the host/harness enforces every item)

- [ ] **User consent** recorded before a server is connected and before privileged tools run.
- [ ] **Tool allowlist** — only explicitly permitted tools are callable, not the whole advertised menu.
- [ ] **Approval gates** on every write/external/destructive/financial/privileged tool (draft → commit).
- [ ] **Result truncation** with a hard cap, independent of what the server returns.
- [ ] **Secret redaction** on inbound results *and* outbound args — credentials never reach the model or the trace.
- [ ] **Logging** of every call: tool, args (redacted), risk class, permission decision, outcome.
- [ ] **Server trust boundaries** — first-party vs. third-party classified; third-party servers start at minimum privilege.
- [ ] **Side-effect classification** attached to every tool at registration; unclassified ⇒ treated as highest risk, not lowest.

## Install-time caution

Do not pipe an untrusted third-party install script straight to a shell (`curl … | sh` off a random mirror). Server mirrors get taken over; a namespace-squatted install script runs as you, before any harness gate exists. Prefer the canonical upstream, pin a known version, and verify the artifact.

## See also

- [permissions-and-risk.md](permissions-and-risk.md) — the risk taxonomy and permission matrix every MCP tool is classified against.
- [tool-design.md](tool-design.md) — non-collapsing naming, typed params, and result/error/blocked envelopes, all of which apply identically to MCP tools.
