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
  Diff gates: run `nitpicker` from the branch. It reviews
  uncommitted changes plus branch commits vs the default branch — scope the prompt when the
  gate targets less. It uses universal default review criteria.
  Everything else (options, plans, positive confirmations, surveys): `nitpicker ask
  [--context-file <path>] "<question>"` — ask preserves dissent, and --context-file carries
  docs that live outside the repo. A GitHub PR: `nitpicker pr --no-comment [<url>]` —
  drop --no-comment only when the user asked to post the review. Existing code with
  no diff: `nitpicker --analyze <path>`. At gates, demand an explicit confirmed/refuted verdict;
  anything short of explicit confirmation is a block.
  nitpicker is built for agent callers — bounded report, meaningful exit codes, session
  persisted under ~/.nitpicker/sessions — so defensive wrappers only subtract. Run it
  bare and foreground and read the full report: `| tail` masks the exit code and cuts
  findings; retry/`until` loops retry away a block; backgrounding adds polling for nothing.
  Verdict contract: non-zero exit (1 hard failure, 3 degraded) is reviewer failure — fail
  closed. Exit 0 means the run was healthy; the only no-findings pass is the exact output
  `No findings. Great job! 🎉` — anything else is findings to triage.
EOF
    ;;
  codex) cat <<'EOF'
codex
  Invoke the `codex:codex-rescue` background agent (Agent tool) with the target and the
  adversarial framing in its prompt. No reply or a non-verdict reply is a block — fail closed.
EOF
    ;;
  opencode) cat <<'EOF'
opencode
  Run `opencode run "<target + adversarial framing>"`. Non-zero exit or no verdict is a
  block — fail closed.
EOF
    ;;
  *)
    echo "unknown reviewer: $choice (expected nitpicker, codex, or opencode)" >&2
    exit 1
    ;;
esac
