---
name: wrap-up
description: End-of-session wrap-up - find what this session left running or lying around, surface unfinished work before it is lost, and propose fixes to skills, CLAUDE.md, hooks, or settings for context gaps the session exposed. Manual trigger only; proposes everything and changes nothing without approval.
argument-hint: "[focus]"
disable-model-invocation: true
---

# wrap-up

Focus: $ARGUMENTS

Wrap up **this session**: things it created, promised, or tripped over. Not a repo audit — long-lived strays that predate the session get one line at most. Everything below is read-only until the user approves the decision list.

## 0. Recall

Build the session's ledger from your own context first: repos and hosts touched, commands with side effects, files written, background work, subagents spawned, promises made, user corrections. After compaction, start from the summary's pending items.

Then add leads from the transcript: `uv run --no-project python ${CLAUDE_SKILL_DIR}/references/session_leads.py ${CLAUDE_SESSION_ID}`. It pattern-matches the transcript and its subagents' transcripts for worktrees, containers, databases, ssh hosts and what was created there, mutating calls to shared services, installs and builds outside the main checkout, unfinished background jobs and subagents, and user messages sent mid-turn. Both precision and recall are imperfect: a lead may already be cleaned up (step 1 verifies it), and anything the patterns do not know is missing — an empty section never means nothing was left. Exit 2 means it could not read the transcript; say so and continue from memory.

The session scratchpad is small and lives in `/tmp`; leave it alone. Worktrees, databases, containers, remote resources, and dependency or build trees outside the main checkout are what matter.

## 1. Leftovers

Check live state for every ledger item, across every repo and host the session touched, sibling repos included:

- **Git**: `git worktree list`, local branches vs PR state (merged → removable), unpushed commits (especially on the default branch), stashes, uncommitted edits in run-created worktrees.
- **Processes**: background tasks and watchers, `nohup` jobs, dev servers and port listeners, containers, hung browsers.
- **Files**: scratch outputs written into the project, secrets copied around (`.env`), run docs and handoffs in `/tmp`, debug prints left in code.
- **Remote and shared state**: dirs, venvs, caches, installed packages on ssh hosts; tickets, test records, messages created on shared services (staging, Slack, trackers).
- **Build trees**: `node_modules`, `target/`, venvs created outside the main checkout — usually inside a worktree that is itself removable.
- **Valuable output in ephemeral places**: anything worth keeping that sits only in the session scratchpad.

Sentinels, run docs, or worktrees from another run are flagged, never touched.

## 2. Loose ends

- Questions to the user that never got an answer, including decision batches buried under notifications — restate them verbatim.
- Promises and blocked items: "later", "once X", "ready when", "not yet verified", "say go".
- Verifications nobody owns ("next nightly will show").
- Subagents whose results never arrived or were never acted on.
- Review findings skipped or deferred, and caveats reported but not resolved.

For each, propose a durable home: the project's tracker, the PR description, a handoff in the repo — not a note in chat.

## 3. Context gaps

Signals: user corrections and frustration, facts the user had to supply, env quirks that took two or more attempts, guard or classifier refusals, skill or tool errors, wrong claims about the project's own design.

For each signal, check the existing instructions (global and project CLAUDE.md / AGENTS.md, loaded skills, hooks, settings) and classify it:

- **missing** — nothing covers it;
- **ignored** — an instruction exists and was not followed; propose sharper wording or a mechanical check, not a duplicate;
- **stale** — an instruction is wrong now; propose the correction;
- **harness** — a hook, guard, or permission caused the friction; propose the rule change.

Keep only gaps that recur or cost real turns; one-offs get dropped. Each survivor gets a target file and the exact line(s) to add or change. Prefer the narrowest owner: a project fact goes in the project file, not the global one.

## 4. Decide

One message, numbered, grouped as Cleanup / Loose ends / Gaps. Each item states its exact scope — what gets deleted, killed, filed, or edited, and where — so approval is never a bare "go". Mark items that are destructive or outward-facing (remote deletes, posting, PRs in team repos). End with nothing else.

Do only what the user approves, then report each item as done, skipped, or failed. Nothing to report in a section → say so in one line.
