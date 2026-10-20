#!/usr/bin/env bash
# Resolve the external reviewer for a run and print how to drive it.
# Priority: nitpicker > codex > opencode. First line is the reviewer name;
# the rest is its invocation contract. Exits 1 when none fits.
# Usage: get_reviewer.sh [repo] [reviewer] — name a reviewer to skip detection.
set -euo pipefail

repo="${1:-.}"
choice="${2:-}"

fits_nitpicker() {
  command -v nitpicker >/dev/null 2>&1 &&
    { [[ -f "$repo/nitpicker.toml" ]] || [[ -f "$HOME/.nitpicker/config.toml" ]]; }
}

if [[ -z "$choice" ]]; then
  if fits_nitpicker; then
    choice=nitpicker
  elif command -v codex >/dev/null 2>&1; then
    choice=codex
  elif command -v opencode >/dev/null 2>&1; then
    choice=opencode
  else
    echo "no reviewer found: install nitpicker, codex, or opencode" >&2
    exit 1
  fi
fi

case "$choice" in
  nitpicker) cat <<'EOF'
nitpicker
  Diff gates: run `nitpicker` from the branch. It reviews uncommitted changes plus branch
  commits vs the default branch, and has no base flag. `--prompt "<...>"` (there is no
  positional prompt) carries the gate's review criteria and refute instruction — always pass
  them, since the built-in criteria are generic — plus a scope note when the gate targets
  less. A gate whose diff is not "uncommitted + branch vs default" (another base, one
  cluster's change) goes through `ask` with the diff written to a file and passed as
  --context-file.
  Everything else (options, plans, positive confirmations, surveys): `nitpicker ask
  [--context-file <path>] "<question>"` — ask preserves dissent, and --context-file carries
  docs that live outside the repo. A GitHub PR: `nitpicker pr --no-comment [<url>]` —
  drop --no-comment only when the user asked to post the review. Existing code with
  no diff: `nitpicker --analyze <path>`.
  nitpicker is built for agent callers — bounded report, meaningful exit codes, session
  persisted under ~/.nitpicker/sessions — so defensive wrappers only subtract. Run it
  bare and foreground and read the full report: `| tail` masks the exit code and cuts
  findings; retry/`until` loops retry away a block; backgrounding adds polling for nothing.
  Verdict contract: non-zero exit (1 hard failure, 3 degraded) is reviewer failure — fail
  closed. Diff, PR, and analyze runs: exit 0 with the exact output
  `No findings. Great job! 🎉` is a clean pass; anything else is findings to triage. `ask`
  gates: demand an explicit confirmed/refuted verdict in the question; anything short of
  explicit confirmation is a block.
EOF
    ;;
  codex) cat <<'EOF'
codex
  Run `codex exec --sandbox read-only -C <repo> "<target + review criteria + adversarial
  framing + 'end with an explicit confirmed/refuted verdict'>"` in the foreground; for a diff,
  name the exact range (`git diff <base>...HEAD`, or uncommitted changes) in the prompt.
  Non-zero exit, no reply, or no explicit verdict is a block — fail closed.
EOF
    ;;
  opencode) cat <<'EOF'
opencode
  Run `opencode run "<target + review criteria + adversarial framing + 'read-only: do not
  modify any file' + 'end with an explicit confirmed/refuted verdict'>"` in the foreground.
  Snapshot the tree before and after — `git status --porcelain` plus
  `git ls-files -mo --exclude-standard -z | xargs -0 shasum` — any difference means it wrote to
  the tree — discard nothing yourself, treat it as a block and surface it. Non-zero exit or
  no explicit verdict is a block — fail closed.
EOF
    ;;
  *)
    echo "unknown reviewer: $choice (expected nitpicker, codex, or opencode)" >&2
    exit 1
    ;;
esac
