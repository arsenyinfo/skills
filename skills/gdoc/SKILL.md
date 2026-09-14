---
name: gdoc
description: Use the local gdoc CLI to find, read, create, edit, review, comment on, share, export, or synchronize Google Docs and Drive files. Trigger for Google Docs or Drive work when gdoc is available; do not use for unrelated local document files or browser-only editing.
---

# gdoc CLI

Use `gdoc` through the shell. Do not substitute browser automation or MCP unless the user requests it.

## Start safely

1. Confirm the CLI is available with `command -v gdoc`. If it is missing, report that and provide the upstream installation command only when useful.
2. Treat the installed CLI as the syntax authority. Run `gdoc --help` or `gdoc <command> --help` before using an unfamiliar option; do not rely on a memorized command catalog.
3. Accept either a Google Docs/Sheets URL or a bare file ID. Resolve names with `gdoc find` or `gdoc ls`; do not guess when multiple files match.
4. If multiple accounts may be configured, use `--account` when the user identifies an account. Do not infer an account for sharing or other consequential changes.

Authentication is a user setup boundary. When gdoc reports that authentication is missing or expired, explain the relevant `gdoc auth` command. Do not delete credential or token files as a troubleshooting shortcut.

## Choose output intentionally

- Use terse default output for ordinary interaction.
- Use `--json` when values will be parsed or passed into another operation.
- Use `--plain` for stable TSV or raw-text matching.
- Use `--verbose` for diagnosis or details, not by default.
- Avoid `--quiet` during collaborative editing because it suppresses gdoc's change-awareness checks. Use it only when the user requests reduced API traffic or a controlled batch workflow makes the tradeoff clear.

## Read and inspect

- Start document work with `gdoc info DOC` and an appropriately scoped `gdoc cat DOC`.
- Use `gdoc cat DOC --comments` when comments or review context could affect the task. Add `--all` only when resolved comments matter.
- For multi-tab documents, run `gdoc tabs DOC`, then target a tab with `--tab` or deliberately read all tabs with `--all-tabs`.
- For spreadsheets, use `gdoc tabs` and a narrow `--range` when possible.
- Use `--max-bytes` for reconnaissance on large documents, then retrieve the relevant tab or range without truncation before editing it.
- Use `gdoc structure` only when native document structure, styles, or exact Docs API ranges are genuinely required.

## Modify with the smallest operation

Read the current target immediately before changing it. Pay attention to gdoc's pre-flight banner; if it reports external edits, refresh the relevant content before proceeding.

Prefer operations in this order:

1. `gdoc edit` for a targeted committed replacement.
2. `gdoc suggest` when the user asks for reviewable suggested edits and the OAuth project supports the required preview API. If suggesting fails, do not silently fall back to a committed edit.
3. `gdoc insert` to add content without replacing existing content.
4. `gdoc write` only when the user intends to replace an entire document or tab.

For `edit`, use text observed from the current document. The command matches raw document text; inspect `gdoc cat DOC --plain` when formatted Markdown output obscures the match. Prefer a unique exact match. Use `--all`, `--normalize`, cell addressing, or file-backed text arguments only when their effect is intended.

Full-document `write` is destructive and can collapse a multi-tab document. Prefer `--tab` for a scoped replacement. Never use `--force` or `--force-collapse-tabs` without explicit user authorization after explaining the consequence.

After a mutation, verify the smallest relevant result with `cat`, `info`, `comments`, or another read-only command. Do not claim success from exit status alone when the resulting content matters.

## Comments and collaboration

- Use `comments` or `cat --comments` to understand existing discussion before replying or resolving.
- Add a comment, reply, resolve, reopen, or delete only when requested or clearly required by the user's stated workflow.
- Preserve comment IDs exactly. Re-read a thread before resolving it when collaborators may have replied.
- Treat suggestions and comments differently: a suggestion proposes a content change, while a comment starts or continues discussion.

## Sharing and Drive organization

Sharing, moving, renaming, copying, and creating files change external state. Perform them when the user requests that outcome, using the narrowest scope:

- Prefer sharing with a named email over domain-wide or public access.
- Use `--domain`, `--anyone`, or `--discoverable` only when explicitly requested.
- Confirm the intended role (`reader`, `commenter`, or `writer`) rather than defaulting consequential access.
- Verify the target file and destination folder before `mv`, `rename`, or `cp` when names or IDs are ambiguous.

## Local files, revisions, and diffs

- Prefer `pull`, `push`, and `export` over ad hoc shell redirection when their semantics fit the task.
- Inspect `revisions` before selecting a historical revision. Revision IDs are sparse and old unpinned revisions may be unavailable.
- `gdoc diff` follows `diff(1)` semantics: exit code 1 means differences were found, not that the command failed.
- Do not overwrite an existing local output file unless the user requested it or its replacement is an obvious part of the workflow.

## Errors

Preserve the relevant command, exit code, and stderr when diagnosing failures. Distinguish authentication errors, API permissions, missing files, ambiguous matches, conflicts, and transport failures. Use current command help and, when needed, a narrow read-only reproduction before proposing credential resets or broad permission changes.

Upstream documentation: <https://github.com/LucaDeLeo/gdoc>
