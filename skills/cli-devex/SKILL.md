---
name: cli-devex
description: >-
  Design, implement, and review command-line interfaces used by humans, scripts,
  CI, and AI agents: minimal surface and defaults, layered tuning, command
  grammar, configuration precedence and trust, help, streams and machine
  output, terminal progress, non-interactive execution, exit codes, crash-safe mutations, and CLI contract tests. Use when
  creating a CLI or changing its arguments, help, output, prompts, config,
  terminal UX, or subprocess/agent-facing behavior. Not for merely using an
  existing CLI.
metadata:
  version: "1.0.0"
---

# cli-devex

**One operation model, two presentations.** A CLI has a human presentation and a
machine presentation of the same operations; it is not a human tool plus an
incompatible API bolted on. A program calling it (script, CI, agent) must be able
to discover an operation, supply inputs, read the result, and recover from
failure without scraping a table, answering a prompt, or guessing whether a
mutation happened.

These are defaults for new behavior, not license to break an established
contract. Follow repo conventions; surface conflicts instead of redesigning
silently. A small tool stays small: apply the slice the change needs.

## Doctrine

1. **Zero-config first run.** With no flags the tool does the obvious thing
   against the current directory, or names the one thing it needs. If the
   first run requires a config file, the defaults are wrong. Detect (env vars,
   sibling tools' auth, a running local server) instead of asking.
2. **Less surface is better.** Every flag, subcommand, config key, and output
   field is a promise to maintain and a decision forced on the caller. Add one
   when a real workflow needs it and no existing control composes into it;
   remove what nobody uses. A negative flag on a good default beats a mode
   enum.
3. **Tuning is layered, never required.** Defaults, then a few flags for the
   common variations, then a config file for persistent preferences, then
   environment for deployment. Each layer is optional and discoverable from
   help; nothing in a deeper layer is needed to use a shallower one.
4. **The Unix way.** Do one thing. Compose through stdin, stdout, files, and
   exit codes. Text by default, structured on request. Behave well under
   pipes, `xargs`, `jq`, `timeout`, and cron. Do not grow a shell, a daemon,
   or a package manager inside the tool.
5. **Boring over clever.** No detection that silently changes behavior, no
   wizards, no surprising side effects. Prefer existing conventions
   (`--json`, `NO_COLOR`, `--`, `-` for stdin) over novel ones.

## 1. Start from journeys

Before touching the parser, read the existing commands, help, tests, parser and
rendering dependencies, and compatibility promises. Then sketch four
transcripts: the common task, one likely failure, an unattended run with stdout
piped, and the caller's next command after that failure. Answer:

- What is inferred, what must be explicit? Consequential targets (account,
  environment, destination, base revision) are explicit or visibly reported.
- What is the result, and what is commentary about producing it?
- What mutates, what can partially fail, and how does the caller recover?
- What must hold for a caller with no terminal, no memory of previous calls, and
  a bounded time and output budget?

Implement the smallest coherent change. Separate results from presentation;
centralize output policy when several commands share it.

## 2. Command grammar

- Root is the default action when the tool has one obvious task; subcommands are
  for the rest. Modes of the default action are flags, not subcommands. Do not
  mirror an internal class hierarchy or an HTTP surface into the command tree.
- Positional operands for the one or two obvious inputs; named options for
  modifiers. `--long-name` always; short aliases only for daily flags. `-h` /
  `--help` and `--version` always. `-v` is verbosity, so the version alias is
  `-V` or nothing.
- Use the parser's facilities: types, choices, ranges, required, conflicts.
  Reject unknown options; suggest, never execute a guess. No implicit
  abbreviation. Validate at parse time: a count that must be positive is a value
  parser, not a runtime "all work failed" after full setup.
- Units and sentinels live in the value: `--timeout 30s`; say what `0` means.
- Repeated flags replace, accumulate, or reject, decided and tested.
  Comma-splitting plus repetition is fine when documented; then reject commas in
  names.
- **Parser-global versus repeatable.** In clap and similar, a global argument
  keeps one occurrence list, so a repeatable flag split around the subcommand
  silently drops the root's values. Global scalars are fine; repeatable flags are
  flattened at each site and merged in command-line order.
- **Root-position flags a subcommand ignores are rejected at runtime.** The
  parser accepts `tool --preset x sub` even when `sub` has no presets; the tool
  must bail, not discard. Test that the rejection fires before config load.
  Making a flag global widens what every subcommand accepts; re-check each one.
- Complex payloads come from a file or stdin (`--request-file f.json`, `-` for
  stdin), never nested shell quoting. Reject unknown fields in owned schemas.
- Never reinterpret argument values as shell; use argv arrays for subprocesses.
  A subprocess surface exposed to an LLM rejects shell operator tokens (matched
  as whole tokens, so `--format=%h|%an` survives) and names the alternative.

## 3. Defaults and configuration

- Defaults favor the common low-risk workflow, and a first run needs no flags
  to be useful. Infer local context when unambiguous; never resolve ambiguity
  by picking a production target or a broad scope.
- No-argument behavior is chosen: a safe obvious operation, or orientation.
  Never a wizard, never a mutation. An informative root invocation succeeds;
  missing operational input fails.
- Config only when persistent settings solve a real need. Precedence: explicit
  `--config` > project file > user file > built-in. First match wins, and **a
  malformed file at any tier is fatal**, never a silent fall-through. Distinct
  messages for absent (naming the command that creates one) and malformed.
- **Validation order is a contract**: usage errors, then config structure, then
  derived settings, then credentials, then anything that touches the network.
  Cheap failures first, so a typo never costs a clone or an API call. A test
  pins the order with a deliberately broken config present.
- CLI booleans override config in both directions. `cli || config` means the
  file cannot be undone from the command line; provide `--no-x` or a tri-state.
  Preserve unspecified versus explicitly false.
- **Config from an untrusted tree is not policy.** When the working tree is
  target-controlled (a stranger's PR, a cloned repo), repo-level config can
  redirect endpoints, neuter limits, or inject into trusted prompt slots. Read
  policy from a trust anchor (the base branch over an authenticated transport,
  or the user's own file), warn when the tree's copy diverges, and never open
  config from that tree via the filesystem: a committed symlink to `/dev/zero`
  hangs the run before it starts. Anything naming a network destination
  (telemetry endpoint) stays out of repo config entirely.
- `init` writes a template reflecting what was detected, never clobbers an
  existing file, rejects flags that make no sense for it, and emits
  undetected-but-known options as commented-out blocks.
- Platform directories; separate config, cache, and state. Per-run writes
  (sessions, trajectories) are opt-in and documented for subprocess callers.

## 4. Help and discovery

- Help and version work offline, without credentials, a project, or valid
  config, and are parsed before any expensive setup. Help goes to stdout with
  exit 0; a usage error is a focused stderr diagnostic with the parser's exit.
- Root help orients; subcommand help suffices to perform the task: purpose,
  usage, options with their effects (not just names), defaults and their
  source, env vars, two realistic examples. No secret as a displayed default.
- **Every argument has help text, and a test asserts it.** Derive parsers pick
  up doc comments; a struct without one inherits the last flattened struct's
  comment as the About line. Duplicated flag structs need duplicated help.
- Help discloses side effects and non-interactive requirements. Discovery is
  progressive: root, command, request and response shape. Schema inspection
  only for a large or dynamic surface, generated from the definitions that
  parse.
- Completions and generated docs from the parser for a multi-command daily
  tool; never edit shell startup files.

## 5. Streams and machine output

- stdout is the result; stderr is commentary. Help, requested logs, and
  dry-run plans are results. No banners, spinners, or update nags in the data
  stream.
- Human output: a summary, units, copyable identifiers. Distinguish empty,
  unchanged, skipped, partial, and failed.
- One explicit machine format (`--json` or `--format json`), never inferred
  from a pipe. TTY detection changes decoration and layout only, never records,
  targets, or meaning. No LLM-detection heuristics; an agent profile, if any,
  composes documented flags and never widens authority.
- **The output contract is checked before TTY detection.** Machine mode owns
  every byte of stdout even inside a PTY: no title escape, no cast line, no
  spinner frame precedes the document.
- JSON is one document (or documented JSON Lines), serialized rather than
  rendered, valid, free of ANSI, flushed before exit. Field names, types,
  nullability, ordering, and absent-versus-null are public. Omit optional keys
  rather than emitting `null`. Bump `schema_version` when a field changes
  meaning, not only when keys change.
- **Every failure in machine mode still produces one envelope**, including
  config-load and auth failures, with a non-zero exit. The write is
  best-effort: a consumer who cannot read the envelope still gets the exit.
- Side effects run before the envelope is emitted so it reports their real
  outcome (`comment_posted: false`), not a success-looking object followed by a
  late failure. Decide separately whether a failed side effect after a
  successful core result is fatal in text mode.
- Metering fields state their accuracy ("lower bound: successful completions
  only"). Compact numbers on progress lines; exact numbers in logs and JSON.
- Bound listings: filter before listing, limits and field selection for large
  results, disclosed continuation. Never clip serialized output at a byte limit
  or disguise a partial page as empty. Large artifacts go to a file and return
  a receipt.

See [machine contract](references/machine-contract.md) for envelope shapes.

## 6. Terminal presentation and progress

- Detect capabilities per stream: stdout may be piped while stderr is a
  terminal. Color, animation, and permission to prompt are three separate
  decisions. Resolve them into one capabilities value early and pass it down;
  inline `isatty()` calls are untestable.
- Color honors nonempty `NO_COLOR`; `TERM=dumb` means no color and no cursor
  control. Every renderer on the path obeys the same gate (a markdown skin that
  always emits ANSI is a leak). Never color as the only status cue.
- Progress goes to stderr. Measured counts when available, a labeled spinner
  otherwise; state phase and elapsed; never fabricate percentages. Delay first
  paint so fast commands do not flash; throttle redraws; one display
  coordinates concurrent tasks; keep a final line after clearing.
- **Log lines suspend the live region.** Route the logger through a writer that
  pauses the progress display around each write, so logs and spinners share
  stderr without corruption. Verbose hides bars and shows logs; non-TTY stderr
  gets sparse newline-delimited phases.
- Width: `COLUMNS` is a shell variable that is usually not exported; treat it as
  an override, then ask the terminal. Truncate by display width, not chars.
- A terminal title, if used, appears only in human text mode on a TTY, is off
  for dumb and linux terms, and is sanitized (controls, bidi, zero-width,
  bounded length) before entering the escape sequence. The previous title
  cannot be read back; clear it on exit.
- Quiet removes commentary, never failures or requested data. Verbose adds
  troubleshooting detail, never secrets. Concurrent verbose streams are
  buffered per lane and printed on completion; interleaved is unattributable.

## 7. Interaction and safe actions

- Every workflow is expressible without a prompt. Prompt only with a usable
  terminal on both ends; never in CI, machine mode, or no-input mode, even
  inside a PTY. Missing input or credentials fail with the fix named, not a
  hang or an implicit browser login. Check the auth of a required helper
  (`gh auth status`) before starting work, not after the first failed call.
- Controls stay distinct and exist only when the capability does: `--no-input`
  (ask nothing), `--yes` (approve a documented confirmation class), `--force`
  (relax one named safeguard). Non-interactive is not consent.
- Preconditions before mutating a user's tree in place: clean working tree
  (print the porcelain), fresh remote state (a stale base is fatal, with the
  workaround named in the error), and a lock.
- **Locks**: advisory `flock` held for the process lifetime; the kernel releases
  it on crash, so no pid bookkeeping and no TOCTOU window. Never unlink the lock
  file (a racer would lock a fresh inode). Key it by the shared store, not the
  worktree path.
- **Restore on every exit path with Drop or finally guards.** Namespaced
  branches; private fetch refs (a shared `FETCH_HEAD` can be rewritten by an
  IDE autofetch between fetch and checkout). Guard declaration order encodes
  unwind order: restore HEAD, then remove the temp dir, while the lock is still
  held. When restore fails, print the exact recovery command.
- Dry run performs no promised mutation, discloses what it could not validate,
  and is neither consent nor a lock. Revalidate at execution.
- Read-only surfaces are safe by construction, not by argument validation. If a
  subcommand's read and write modes cannot be told apart by arguments, remove it
  and serve the query through plumbing with no write mode. Reject absolute paths
  and `..` in arguments globally; deny by name the flags that read outside the
  sandbox.
- No unsolicited update checks, telemetry, dependency installs, or remote work
  during local commands. Telemetry is activated by environment only and exports
  identifiers and counts, never content.

See [safety](references/safety.md) for trust boundaries and guard patterns.

## 8. Failure, exit codes, recovery

- An error names the operation or input, the cause, and the next safe action.
  Stack traces only in debug. Distinguish bugs from user mistakes.
- **Exit codes do not collide with the parser.** If the parser exits 2 on usage
  errors, the tool's own codes avoid 2. Baseline: 0 clean, 1 hard failure (no
  result), 3 degraded (result produced, something failed). Degraded is a
  distinct exit, not a warning inside 0, and also a field in the envelope.
- A flush failure on the result is a hard failure, not degraded. `main` is
  synchronous: parse, init telemetry, run, drop the runtime, shut down
  telemetry, map the outcome to an exit. Never `process::exit` past a guard.
- **Total failure is an error, not an empty success.** When every unit of work
  failed, refuse to synthesize a result; persist the failure record first,
  since that run is the one that most needs a durable record.
- Partial failure: isolate per unit (one dead worker fails its own job, others
  proceed), keep failure stubs out of the synthesized result, and carry them in
  coverage fields plus the degraded exit. Return per-item outcomes so recovery
  never repeats committed effects.
- Retry classifiers read structured fields (code, type, status) only, never
  rendered error text. Exact codes are permanent or transient; an unknown 429
  gets the long backoff. Each retry is a log line with attempt, backoff, and
  cause. Retry mutations only when idempotency makes it safe; on an ambiguous
  outcome, check status rather than repeat.
- Failover rings: the final error names the whole attempted chain; a successful
  failover is not degradation (no evidence was lost); dedupe repeated warnings.
- Budgets: when a loop is about to exhaust its turn or token budget, tell the
  worker to wrap up rather than return nothing. Turn a blank response into a
  diagnosis ("reasoning consumed the output budget; raise the limit").
- Cancellation restores terminal state, stops owned work, reports remote work
  still running, and never claims a rollback that did not happen. A broken
  pipe exits cleanly under a documented policy.

## 9. Callers that are programs

Support discover, inspect, act, verify or recover; add only what the domain
needs.

- Document the subprocess contract in one place: streams, exit codes, the
  one-line envelope, that stdin is never read, side-effect writes and how to
  disable them, and that a timeout must kill the process group (blocking child
  processes do not get the signal otherwise).
- Calls are independent: explicit IDs, paths, base revisions, and context per
  call; no mutable "current" selection; handles come back in the form follow-ups
  accept. Unique temp dirs per process so concurrent runs do not collide.
- **Tools never encode failure as successful text.** A result whose status
  depends on sniffing the body for `Error:` is wrong in both directions.
- **Success is a structured field, not a sentinel string.** If callers must
  string-match a phrase to learn the verdict, the contract is missing a field.
- Structured recovery: stable error code, field path, truthful outcome
  (`not_started`, `partial`, `unknown`), operation handle. A timeout is not
  proof that the remote mutation failed.
- Untrusted content stays data: wrap repo-authored or remote text in a delimited
  block and escape the closing delimiter inside it; escape quotes in
  attributes. Keep CLI-generated status apart from third-party text. No
  `next_command` strings built from remote content. Serialization preserves
  syntax, not trust; say so.
- Out-of-sandbox inputs (`--context-file`): eager hard failure on a bad path
  before any expensive work; regular files only, checked by fstat on the opened
  descriptor, opened non-blocking so a FIFO cannot hang; a byte budget metered
  on the serialized block. Decide and document who sees them.
- A CLI confirmation, application authorization, and harness approval are three
  boundaries; none substitutes for another.

## 10. Verification and handoff

Test observable behavior: stdout, stderr, exit status, side effects,
interaction. Parser unit tests alone are insufficient.

- Subprocess tests for real streams and status; PTY tests for prompts,
  progress, and cancellation; both with deadlines. Isolate HOME, config, cwd,
  and network.
- Pin contracts as tests: exit-code mapping (including a failing-flush writer);
  validation order with a malformed config present; inapplicable flags rejected
  before config load; one-line envelope on every failure path; absent versus
  null keys; repeatable-flag merge order; help text on every argument;
  `NO_COLOR` and `TERM=dumb`; guard behavior on drop; a regression fixture per
  bypass found (a committed symlink to `/dev/zero`, a forged closing tag).
- Parse JSON in tests; a snapshot is not a schema check. Normalize only
  genuinely unstable fields.
- For agent-facing tools, run a cold-start exercise: task plus executable name
  only; judge final state and forbidden side effects; inspect calls for guessed
  flags, table scraping, unsafe retries. Deterministic tests remain the
  baseline.

See [verification](references/verification.md) for the scenario matrices.

Handoff:

```text
UX decisions: <defaults, modes, contracts chosen>
Examples: <human invocation; machine discover/act/recover path>
Compatibility: <preserved / intentionally changed>
Verified: <tests run and outcomes>
Not verified: <platform, terminal, integration cases>
```
