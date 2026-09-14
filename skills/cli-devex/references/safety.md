# Safety: trust, locks, guards, retries

Patterns for a CLI that mutates a user's tree, runs against content it does
not own, or exposes tools to a model. Each pattern is stated with the failure
it was introduced to prevent, because the failure is what tells you whether the
pattern applies.

## Trust anchors for configuration

Repo-level config is convenient and, in any flow where the working tree is
target-controlled, an attack surface: a `base_url` override exfiltrates keys,
a lowered limit neuters review, a per-name prompt override injects into a
trusted rubric slot.

- Decide per flow where policy comes from. Reviewing the user's own branch: the
  tree is theirs, read the file. Reviewing a PR: the tree holds the PR head;
  read the config blob from the base branch via git objects, fall back to the
  user's global file, and keep an explicit `--config` path trusted as given.
- A base branch is a trust anchor only when `origin` is the authenticated
  remote the metadata came from. Match on transport, not on host string:
  `https` and `ssh` qualify; `git://`, `http://`, `file://github.com/...`
  (local, attacker-writable), and remote-helper syntax `host::address` do not.
- Never open the tree's copy of the config through the filesystem, even to
  compare it. Compare object ids. A committed symlink to `/dev/zero` turns a
  stat-then-read into a hang; the regression test commits exactly that.
- Warn when the tree's config diverges from the anchor and say which one was
  used. Absent is quiet; unresolvable anchor is a warning, because policy could
  not be consulted at all.
- Data-only sections (`[presets.<name>]`) reject unknown fields so they cannot
  grow into routing or credential overrides by accident.
- Nothing that names a network destination belongs in repo config.

## Untrusted content in prompts and output

- Repo-authored context (`CLAUDE.md`, `AGENTS.md`, issue bodies, filenames,
  remote error text) is wrapped in a delimited block that marks it as reference
  material, and the closing delimiter is escaped inside the block so the
  content cannot end its own container. Escape quotes in attributes. Pin both
  with tests that assert exactly one closing tag survives.
- CLI-generated status and remediation stay separate from third-party text.
  Prefer codes and reference objects to shell-ready `next_command` strings that
  interpolate remote content.
- Human renderers do not interpret attacker-controlled markup or control
  sequences. Untrusted path components are sanitized (controls, bidi
  overrides, zero-width, bounded length) before entering an escape sequence.
- Serialization preserves syntax, not trust. A sanitizer is an optional
  defense, never a promise of prompt-injection immunity. Say so in docs.
- Subagents never inherit tools that write into parent-owned state.

## Locks for in-place mutation

- Advisory `flock(LOCK_EX | LOCK_NB)` on a fixed per-target path, held for the
  process lifetime. The kernel releases it on any exit, so there is no stale
  pid bookkeeping and no window between a staleness check and an exclusive
  create. The pid-file scheme it replaces had both, letting two racers each
  delete and recreate the lock.
- Never unlink the lock file: a racer would create a new inode and lock that.
- Key the lock by the shared store (`git rev-parse --git-common-dir`), so
  linked worktrees that share refs share one lock.
- Non-unix fallback is exclusive create; document that a crash leaves a lock
  the user must remove.
- Temp-clone flows need no lock: a unique directory per process.

## Guards and unwind order

- Preconditions first: clean working tree (print the porcelain output in the
  error), fresh remote state (fatal when the fetch fails, with the workaround
  named), helper auth (`gh auth status`) before any git mutation.
- Fetch into a private ref (`refs/<tool>/pr-N-head`), not the shared
  `FETCH_HEAD` that an IDE autofetch can rewrite between fetch and checkout.
  Force the update so a force-pushed head still lands.
- Check out onto a namespaced branch the tool owns. Re-running fast-forwards
  it; a stale copy is force-deleted because it is the tool's namespace, never
  a user branch.
- A restore guard is created the moment state changes and restores on drop,
  so a panic or an early `?` anywhere later cannot strand the user. A detached
  HEAD is restored with `switch --detach`; `switch -- <sha>` refuses a bare
  commit and would strand silently.
- Encode unwind order in declaration order: restore guard, then temp dir, then
  lock. Fields drop in that order, so HEAD is restored and the directory
  removed while the lock is still held.
- When restore fails, the warning prints the exact recovery command.
- Read-only git invocations set `GIT_OPTIONAL_LOCKS=0` so a nominally-read
  `git status` cannot rewrite the index or contend on `index.lock`.

## Read-only tool surfaces

When a tool surface is exposed to a model (or any untrusted caller):

- Safety by construction beats argument validation. If a subcommand's read and
  write modes cannot be distinguished by arguments (`git branch`, `git tag`:
  abbreviations, `=`-glued values, `--`, value-taking flags absorbing the next
  token all leaked ref creation), remove the subcommand and serve the query
  through plumbing that has no write mode (`for-each-ref`, `show-ref`).
- Reject absolute paths and `..` components in arguments across all
  subcommands; flags like `diff --no-index <abs>` and `blame --contents <abs>`
  read straight from the filesystem otherwise. Deny by name, including
  abbreviations, the flags that read or write outside the sandbox; scope
  denials to the subcommands where they are dangerous (`-o` is `--others` in
  `ls-files`).
- Reject shell operator tokens as whole tokens and name the alternative:
  models glue pipes onto commands, and a literal `|` reaching argv either
  fails loudly or succeeds wrongly.
- Every tool failure is a failure result, never `Ok("Error: ...")`. A file that
  starts with `Error:` is not a failure; a failed read is.
- Out-of-sandbox inputs are opened non-blocking and fstat-checked on the
  descriptor (a path swapped for a FIFO between stat and open blocks forever),
  bounded by a byte budget metered on the serialized block, and loaded eagerly
  so a bad path fails before any expensive work.

## Retries, failover, idempotency

- Classify on structured fields (`code`, `type`, HTTP status) only. Exact
  permanent codes skip retries and mark the route unavailable; exact transient
  codes and unknown 429s take the long backoff; a real outer 5xx wins over
  nested upstream data. Never scan rendered error text; a substring match on
  `code` once misclassified `decode` and `unicode` errors as permanent 4xx.
- Each retry is a log line with model, attempt, max attempts, backoff, and the
  cause. Repeated warnings from one exhausted route are deduplicated.
- A failover ring hands completed history to the next route; the final error
  names the whole chain (`a -> b -> c`). A successful failover is observable
  but not degradation.
- Retry a mutation only when a backend idempotency key or version precondition
  makes it safe; preserve the key across transport retries. A separate read
  followed by an unconditional write is not a precondition. On an ambiguous
  outcome, look up status; never treat a timeout as proof of failure.
- Batches state their policy (atomic, best effort, fail fast) and return
  per-item outcomes so recovery never repeats committed work.

## Permission boundaries

- Report identity and scope without revealing credentials. Fail on missing or
  insufficient authority; never silently try a more privileged identity.
- Secrets never appear on command lines, in receipts, in help defaults, in
  snapshots, or in debug logs. Read-only reuse of another tool's token store
  is fine when documented; writing back to it is not.
- A CLI confirmation, application authorization, and harness approval are
  three boundaries. Unattended execution is not a reason to skip any of them,
  and the tool's docs must not advise bypassing them.
