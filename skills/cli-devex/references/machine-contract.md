# Machine contract

The shape a program-facing CLI promises: streams, exit codes, the envelope, and
how they behave on every failure path. Choose one convention per output mode,
write it down, and pin it with tests. Everything below is a pattern with a
stated trade-off; an established contract in the tool wins over any of it.

## Exit codes

Baseline for a new tool whose parser already uses 2 for usage errors:

| Code | Meaning | Consumer action |
| --- | --- | --- |
| 0 | Clean: the operation completed and the result is trustworthy | Proceed |
| 1 | Hard failure: no result was produced | Fail, alert |
| 2 | Reserved for the parser (usage error) | Fix the invocation |
| 3 | Degraded: a result was produced but part of the work failed | Warn, inspect the envelope |

Rules:

- 0 means the run was healthy, not that the domain verdict is positive. A
  review that found bugs exits 0; a check command may document a distinct
  non-error code for "differences found".
- Degraded is an exit code and an envelope field. One without the other forces
  the consumer to parse prose.
- A flush failure on the result is 1, not 3: if the consumer may not have the
  bytes, there is no result.
- Cancellation and broken pipe get their own documented policy; do not let a
  framework default (an interrupt code, a SIGPIPE trace) define it by accident.
- Map outcome to exit in one function, after every guard has dropped. Never
  call `process::exit` from inside the run.

## The envelope

One JSON document per invocation on stdout, one line, flushed before exit.
Everything human goes to stderr. Illustrative fields:

```json
{
  "schema_version": 1,
  "status": "ok",
  "degraded": false,
  "target": {"repo": "owner/name", "number": 42, "head_sha": "abc123"},
  "result": {"report_markdown": "..."},
  "coverage": [{"unit": "security", "attempted": 2, "succeeded": 2}],
  "usage": {"input_tokens": 120000, "output_tokens": 8000},
  "side_effects": {"comment_posted": true},
  "duration_ms": 91234
}
```

- `schema_version` bumps when any field changes meaning, not only when keys
  are added or removed. Additive keys under the same version are fine; a
  redefined `input_tokens` is not.
- Optional keys are omitted, never `null`. "Present iff `status: ok`" is a
  testable rule; "sometimes null" is not.
- Identity fields report what was actually processed (the SHA at `HEAD` after
  checkout), not what the metadata said before the race.
- Metering fields document their accuracy. "Successful completions only, a
  lower bound on spend" is honest; an unqualified total is a lie waiting to be
  discovered.
- `coverage` and similar accounting live in the envelope only. They are
  execution noise, not evidence, and must never be fed back into whatever
  synthesizes the result.
- Success is a field (`verdict`, `findings: []`), never a sentinel phrase the
  consumer has to string-match.

## Failure envelopes

Two valid conventions. Pick one per tool.

**Envelope on stdout for every outcome.** The same document carries
`status: error` and `error`; the exit is non-zero. This is simplest for
consumers: one stream, one parse.

```json
{"schema_version": 1, "status": "error", "error": "no config found — run `tool init`", "duration_ms": 12}
```

**Result on stdout, structured error on stderr.** stdout is empty on a
pre-result failure; stderr holds exactly one JSON document and nothing else.
Requires that no other stderr line be emitted after the error is chosen.

Either way:

- Every failure path yields the envelope, including config load, credential
  validation, and helper-tool checks. Wrap the run in one function that turns
  `Err` into the envelope; do not scatter emit calls.
- The write is best-effort. If stdout is gone, the non-zero exit still stands.
- Do not install a process-wide panic hook that emits an envelope if work runs
  in tasks whose panics are already caught and folded into a degraded result;
  it would double-emit. A genuine top-level panic aborting non-zero with a
  stderr message is an acceptable catastrophic signal.
- A structured error carries a stable `code`, the offending field path when
  known, and a truthful `outcome`: `not_started`, `partial`, `unknown`. A
  generic `retryable: true` is insufficient for a write whose commit is
  unknown.

## Side effects and the envelope

Perform side effects before emitting the envelope so it reports their real
outcome. A comment posted after a success-looking object was written cannot be
reflected in it. A failed side effect after a successful core result is a
warning plus a `false` field in machine mode; whether it is fatal in text mode
is a separate, documented decision.

Machine mode does not imply "no side effects". `--json` and `--no-comment` are
orthogonal; document the embedding recipe that combines them.

## Streams

- Machine mode owns every byte of stdout. Check the output contract before
  TTY detection so a terminal-title escape, a cast line, or a spinner frame
  can never precede the document, even inside a PTY.
- Streaming output uses JSON Lines with documented record types, ordering, a
  terminal record, and mid-stream failure behavior. EOF alone is not
  completion evidence. Never mix progress objects into a mode documented as
  one document.
- Keep stderr commentary sparse in machine mode; a caller may capture both
  streams into a bounded context.

## Listings and bounds

- Record limit, page size, and byte limit are different controls. A short or
  empty page does not prove exhaustion when continuation is present.
- Field selection applies to records, not the envelope; the page metadata
  survives projection.
- Adding a default cap to an export whose contract promised all records is a
  breaking change even though every emitted record still parses.
- Large artifacts go to an explicit destination without implicit overwrite;
  return path, type, and size only when actually known. A host-only path is
  not a handoff to a sandbox that cannot read it.

## Async work

Only when the backend already has durable operations:

- Submission success means accepted; wait success means the promised condition
  was met. Distinguish accepted, running, completed, and wait timed out.
- A status lookup exits 0 when the lookup succeeded, even if it reports a
  failed job; document that the exit describes the lookup.
- A wait deadline does not cancel remote work. Say whether interrupting the
  client stops the job and whether cancellation is requested or confirmed.
- Surface backend idempotency keys and version preconditions as they are; the
  CLI cannot manufacture guarantees the backend lacks, and must not imply them.
