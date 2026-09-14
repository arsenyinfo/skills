# Verification

Select checks relevant to the change and the tool's real features. Do not add
JSON, config, prompts, or a test framework merely to satisfy a matrix. Existing
behavior stays unless the change is intentional and documented.

## Test at the right boundary

- Parser tests for argument relationships (merge order, namespaces, rejected
  combinations). A `debug_assert` on the command definition catches structural
  errors but not missing help text; assert help separately.
- Subprocess tests for the real executable: streams, status, side effects.
- PTY tests for prompts, progress, cancellation. A monkey-patched `isatty` does
  not demonstrate terminal cleanup or signal behavior. Route TTY decisions
  through one injectable value so the branches are also unit-testable.
- Isolated HOME, config, cwd, env, and fake services. Never run destructive,
  billing, publishing, or production operations as UX tests. Deadlines on every
  hang-prone test; drain subprocess streams.

## Contract pins

Tests that exist to stop a documented contract from drifting. Each is cheap and
each has caught a real regression somewhere.

| Contract | Test |
| --- | --- |
| Exit-code mapping | Table over outcomes, including a writer whose flush fails: degraded with a failed flush is 1. |
| Validation order | A deliberately malformed config is present; a usage error still wins, and structure errors surface before credential errors, with the env var name absent from the structure error. |
| Inapplicable flags | `tool --preset x sub` fails before config load for every subcommand that ignores the flag; post-subcommand placement is a parser error. |
| Repeatable-flag merge | Values split around the subcommand arrive in command-line order; comma-splitting expands; repeats append. |
| Execution-flag namespaces | Root and subcommand copies do not leak into each other. |
| Envelope on failure | Every failure path (config, auth, helper missing, runtime) yields exactly one line with a trailing newline in machine mode, and writes nothing to stdout in text mode. |
| Absent versus null | Success-only keys are absent on error, not `null`. |
| Output contract before TTY | Machine mode in a PTY emits no title escape, cast line, or spinner byte. |
| Help completeness | Every argument in the generated command has non-empty help; the root About line is the intended one. |
| Color | `NO_COLOR` absent, empty, and nonempty; `TERM=dumb`; forced color elsewhere cannot corrupt machine output. |
| Guards | Dropping the restore guard switches back to the original branch and re-detaches onto the original commit. Guard struct field order is asserted by a test that observes unwind order. |
| Locks | Two processes on one repo: the second fails immediately with the lock path; linked worktrees share one lock. |
| Bypass regressions | One fixture per bypass found: a committed symlink to `/dev/zero`, a forged closing delimiter, a quote in an attribute, a FIFO at the context-file path (with a watchdog), `git branch --format --list newbranch`. |
| Generated template | Byte-stable against a fixture; changes are deliberate. |

## Core matrix

| Scenario | Observable assertion |
| --- | --- |
| `--help`, subcommand help, `--version` | Succeed offline, without credentials, project, config, or state changes. Help on stdout. |
| Bare root, missing required input | The chosen no-argument contract; missing operational input fails with guidance. |
| Unknown flag, bad type, out of range, conflict | Non-zero, focused stderr, nothing started. Suggestions do not execute. |
| `--opt=value`, separate values, repeats, `--` | Parser agrees with help; dash-prefixed operands unambiguous. |
| Spaces, Unicode, leading hyphens, relative paths | Addressed correctly; displayed legibly; errors keep context. |
| Normal, empty, unchanged, partial, failed result | stdout, stderr, side effects, and status agree. No accidental success for unfinished requested work. |
| stdout piped with stderr terminal, and the reverse | Each stream uses its own capabilities; records and targets unchanged. |
| stdin closed or redirected; CI; explicit no-input | No question, editor, or browser. Missing input fails promptly without consuming piped data as answers. |
| Consumer closes the pipe early | Clean stop under the documented policy; no traceback or flush loop. Enough output to close mid-write. |

## Conditional matrix

| Feature | Observable assertion |
| --- | --- |
| Machine output | Parse actual stdout. Field types, empty shapes, no prose or decoration, no hidden record loss. Failure and mid-stream failure policies. |
| Progress | Fast, slow, stalled, retried, cancelled, failed work. Counts real, logs bounded, final line retained, cursor restored, log lines do not corrupt the live region. |
| Narrow terminal | Output survives narrow widths and missing glyphs; truncation by display width. |
| Quiet, verbose | Quiet keeps errors and requested results; verbose adds context without credentials; concurrent verbose is attributable. |
| Config layers | Provenance, precedence, malformed-file fatality at each tier, explicit-file behavior, unspecified versus false. |
| Confirmations, dry run | Missing confirmation fails unattended; `--yes` does not invent selections; dry run mutates nothing on any path. |
| Cancellation, remote timeout | Bounded shutdown; owned resources cleaned; partial state reported; unknown outcome not mislabeled. |
| Secrets | Absent from help, diagnostics, snapshots, debug logs, exported telemetry. |
| Completions, generated docs | Agree with the parser; generation needs no credentials and edits no shell files. |

## Agent-facing matrix

| Scenario | Observable assertion |
| --- | --- |
| Cold-start discovery | Valid inputs and result shape identifiable from installed help or schema without mutating state. |
| Machine mode in a PTY | No prompt, pager, browser, login, or animation; scope and authorization unchanged. |
| Structured failure | Documented error stream parses for validation, config, auth, denied, runtime errors; code, status, and effects agree. |
| File or stdin payload | Quotes, newlines, Unicode, leading hyphens, malformed input, unknown fields behave as documented; invalid input has no effect. |
| Bounded discovery | Limits and projection keep identity and pagination metadata; nothing silently omitted or clipped. |
| Follow-up handles | A returned ID works in a fresh process with explicit context. |
| Lost response after commit | Fault injection shows the effect happened once; recovery does not induce a duplicate. |
| Partial batch | Per-item results and exit match real effects; recovery targets only unfinished work. |
| Parallel callers | Explicit context isolates calls; temp paths and output files do not race. |
| Untrusted content | Malicious titles, filenames, remote errors remain data; control characters do not corrupt human output. |
| Compatibility | Existing fields, types, empty shapes, codes, default scope, and handles stay compatible unless intentionally migrated with a version bump. |

## Cold-start exercise

In disposable fixtures, give a fresh agent only the task and the executable
name. Try a read task, a scoped mutation, a recoverable input error, and an
ambiguous remote completion. Judge final state and forbidden side effects
independently of the agent's prose. Inspect the transcript for guessed flags,
table scraping, unnecessary large reads, repeated discovery, unsafe retries,
hangs, and bypasses. One successful transcript is a smoke check, not proof.
Skip this for cosmetic changes.

## Snapshots

Fix width; normalize only genuinely unstable fields. Do not normalize away a
semantic difference or approve every changed snapshot automatically. Parse
JSON; a text snapshot is not a schema check. For terminal output, inspect both
the rendered experience and the final retained transcript. Rust: `trycmd` for
command fixtures. Python: Click's test runner for captured streams and
isolated filesystems. Use what fits the existing stack.
