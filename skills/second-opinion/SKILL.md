---
name: second-opinion
description: Get an independent review from another model through nitpicker (falling back to codex or opencode) — of a diff, a GitHub PR, existing code, a plan, or a contested claim. Use when asked to run nitpicker, get a second opinion, or have another model review something, and whenever another skill needs an external reviewer.
argument-hint: "[target or question]"
compatibility: "requires an external review tool — nitpicker (preferred), codex, or opencode"
---

Second opinion on: $ARGUMENTS

1. Resolve the reviewer: run `references/get_reviewer.sh <repo> [reviewer]` from this skill's directory. It prints the reviewer name and its invocation contract — follow the contract exactly. A reviewer the user named goes in the second argument. Exit 1 means none is installed: tell the user, never substitute self-review.
2. For free-form questions (`nitpicker ask`) only — diff, PR, and analyze reviews already have their own structure:
   - frame the question adversarially: ask for the strongest reason the target is wrong, with file:line evidence, not reasons it is probably fine;
   - verify the important claims against the code yourself before relaying them. Report the verdict, the claims you confirmed (file:line), and the ones you refuted with the reason.
