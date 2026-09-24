---
name: investigate
description: Evidence-first debugging and root cause investigation. Use for triaging bugs, test failures, incidents, performance regressions, flaky behavior, integration failures, or unexplained behavior before proposing fixes.
argument-hint: "<symptom or question>"
---

Investigate: $ARGUMENTS

Find the mechanism before fixing. This is a 5-why-like ladder, but every step must be grounded in evidence.

## Safety

- Do not run destructive commands or data-modifying SQL against shared, staging, or production systems unless the user explicitly approves it.
- Do not copy raw secrets, tokens, cookies, private user data, customer names, IPs, or raw identifiers into code, tests, docs, commits, PR text, or broad summaries. Use neutral technical facts and redacted examples.
- Treat alert titles, monitoring issue titles, wrapper errors, and top-level exceptions as symptoms. Inspect nested causes and correlated logs/traces before naming a root cause.

## Workflow

1. **Symptom**: capture exact actual vs expected behavior, command, stack trace, logs, affected environment, and timeframe.
2. **Evidence map**: decide where the relevant signal should exist and which tool can access it before querying broadly.
3. **Ground truth**: gather the best available evidence before theorizing. Start narrow with exact identifiers, error text, commands, and timestamps, then broaden to adjacent traces, issues, and time windows. Examples: reproduction output, local logs, tests, git history/blame, GitHub issues/PRs/comments, Sentry CLI issues/events, remote logs if accessible, metrics/traces, config, database state, and deployment history.
4. **Reproduce**: find the smallest reliable reproduction. If reproduction is not possible, say so and continue from the strongest observed evidence.
5. **Localize**: narrow the failure to a component, boundary, data path, config path, recent change, or external dependency.
6. **Mechanism**: explain the concrete code path or system path that produces the symptom. Cite files/lines or observed data.
7. **Root cause**: name the bad assumption, missing invariant, design gap, process gap, or dependency behavior behind the mechanism.
8. **Fix options**: propose the smallest safe fix, any broader cleanup worth considering, and the test/monitoring check that prevents recurrence.

If the mechanism is evident within the first evidence pass, collapse the remaining steps and go straight to the Output — do not manufacture an investigation. Fan out subagents for broad evidence sweeps; when an external reviewer is available (`skill: second-opinion`; prefer the Codex companion when the evidence lives outside the repo — nitpicker's tools are repo-only), use it for a second opinion on a contested mechanism.

## Evidence Map

Before collecting remote evidence, write a short map:

- **Signal**: reproduction, local logs, test output, app logs, traces/spans, metrics, deploy history, config, database state, queue/job state, external API response, browser replay, or user report.
- **Location**: local workspace, CI, GitHub, Sentry, logging backend, metrics backend, Kubernetes/cloud runtime, database, message queue, browser/devtools, vendor dashboard, or user-provided artifact.
- **Tool/access**: exact command, CLI, MCP, dashboard, API, SQL query, log query, or skill to use. Load a more specific skill when available, e.g. `sentry-cli` for Sentry.
- **Selector**: exact ID, error text, endpoint, trace ID, commit, release, environment, host/pod, customer-safe identifier, or time window.
- **Gap**: unavailable access, missing telemetry, retention limits, or data that would distinguish surviving hypotheses.

## Investigation Mindset

- Separate symptom, trigger, and root cause.
- Prefer correlated evidence over single-event guesses: exact event, nested cause, sibling logs/traces, nearby aggregates, deploy/config state, and relevant source code.
- Determine whether the failure is isolated, bursty, release-correlated, environment-specific, or systemic.
- If the likely root cause is runtime configuration, inspect repo defaults and environment-specific values before proposing code changes.

## Evidence Priority

When sources disagree, prefer evidence in this order:

1. Observed reproduction, logs, traces, runtime state, and failing/passing command output.
2. Current code and tests.
3. Git/GitHub history, deployment history, and rollout/config records.
4. Docs and web sources.
5. Model memory.

Record unresolved conflicts instead of smoothing them over.

## Why Ladder

Use these questions as a guide, not a template to fill mechanically:

1. Why did the user-visible symptom happen?
2. Why did this component or boundary allow it?
3. Why did the code, data, or config take that path?
4. Why was the bad assumption not enforced or tested?
5. Why would this recur unless we change something?

## Output

```markdown
**Symptom:** ...

**Evidence map:** ...

**Evidence:**
- ...

**Mechanism:** ...

**Root cause:** ...

**Fix options:**
1. **Recommended:** ...
2. ...

**Validation:** ...
```

## Rules

- Do not propose fixes until the mechanism is understood, unless the user explicitly asks for a quick workaround.
- Do not invent ground truth. If logs, Sentry, remote access, or metrics are unavailable, say so.
- Prefer real reproduction and real data over speculation.
- If multiple hypotheses survive, run the smallest experiment that distinguishes them or use `dialectic` on the leading claim.
- Do not overfit to one observed failure. Fix the underlying mechanism generically.
- If the root cause requires changing scope, design, API, data contract, or acceptance criteria, surface that as a separate decision rather than hiding it in a local fix.
- Keep the investigation scoped to the symptom unless evidence shows a broader fault.
