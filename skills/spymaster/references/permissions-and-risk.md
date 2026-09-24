# Permissions and risk

The model proposes an action; the harness classifies its risk and enforces permission **before any side effect fires**. The model does not remember permission rules — code does. Approval records live **outside the model-editable prompt**: a compaction, a jailbroken tool result, or a self-edited instruction must never be able to grant an approval. If safety depends on the model choosing to honor a sentence, it isn't safety. Every gate in this file is a deterministic check the execution engine runs, not advice the prompt hopes the model follows.

**Right-size this.** The taxonomy and matrix below are a superset for a harness that can touch shared state, money, or many users. A read-only or local-only agent may only ever hit `read_public` / `read_private` / `local_write` — for that, one written rule ("reads auto-run; the single write path is draft/commit") beats a per-tool matrix. Add classes, rows, and gates as the agent's reach grows; don't stand up the whole apparatus for an agent that can't reach past its own sandbox.

## Risk taxonomy

Every tool carries one **primary class** — its *worst* blast-radius effect, not its typical one — plus, optionally, one or more orthogonal **overlay** tags (`regulated_data`, `security_sensitive`) that ratchet the gate stricter without changing the primary. Baseline primary classes, lowest to highest blast radius:

- **read_public** — reads data anyone could see (public docs, open web, public repo). No side effect.
- **read_private** — reads data behind auth the caller is entitled to (private repo, internal wiki, a user's own inbox). Leaks are the risk, not mutation.
- **local_write** — writes only to the workspace/sandbox the harness owns (scratch file, local branch). Reversible, contained.
- **internal_write** — mutates shared internal state others depend on (shared DB row, staging config, a ticket). Reversible but visible to others.
- **external_communication** — anything a third party receives (email send, Slack post, webhook, comment on a public issue). Irreversible once out.
- **deploy_or_runtime_change** — changes what runs or how (deploy, feature flag, scaling, config that alters live behavior).
- **delete_or_destructive** — removes or overwrites data such that recovery is hard or impossible (drop table, force-push, delete branch/release).
- **financial_or_billing** — moves money or commits spend (payment, refund, provisioning a paid resource, changing a plan).
- **privileged_access** — grants, escalates, or uses elevated authority (add IAM role, share a credential, act as another principal).
And the two overlays, which layer *on top of* whatever primary class applies:

- **security_sensitive** (overlay) — touches auth, secrets, or the security posture itself (rotate/read a key, change a permission policy, edit a firewall rule).
- **regulated_data** (overlay) — reads or moves data under a legal/compliance regime (PII/PHI, payment card data, export-controlled). Set by the *data*, independent of the operation.

When a tool spans two blast-radius classes, its primary is the higher of them. Overlays don't compete with the primary — they stack: a read of PHI is `read_private` (primary) with a `regulated_data` overlay, and the strictest of the applicable gates wins.

## Permission matrix

Every tool gets a row. No tool ships without one. Worked example:

| Tool | Risk class | Side effect | Approval required | Notes |
|---|---|---|---|---|
| `repo.search` | read_public | none | no | Bounded output; auto-run at any level. |
| `repo.write_file` | local_write | writes to local worktree | no (Level ≥2) | Reversible; never writes outside the area. |
| `deploy.prepare` | read_private | none — emits a plan artifact | no | Read-only first half of the draft/commit split. |
| `deploy.commit` | deploy_or_runtime_change | live deploy | **yes, always** | Consumes a `deploy.prepare` artifact + explicit approval. |
| `email.create_draft` | local_write | stores a draft, sends nothing | no | Reviewable artifact; no external effect. |
| `email.send_draft` | external_communication | third party receives mail | **yes, always** | Sends a specific draft ID; approval bound to that ID. |

The `approval required` column is enforced by the permission engine keyed on risk class and environment — not left to the tool's own code and never to the prompt.

## Draft/commit split — this reference owns it

Any action that is irreversible or reaches outside the harness is split into two tools: a **reviewable-artifact stage** and a **side-effect stage**.

- `prepare_deploy` → `deploy`
- `draft_email` → `send_email`
- `preview_migration` → `apply_migration`
- `plan_changes` → `apply_changes`

The first stage is read-only / no external effect: it produces a concrete, inspectable artifact — a diff, a rendered message, a migration SQL, a change plan — and returns it as the observation. The second stage is gated: it takes an artifact reference (a draft ID, a plan hash) and executes only that. Two properties make this real, not decorative:

1. **The commit stage cannot fabricate its own payload.** It acts on the prepared artifact, so what a human reviews is exactly what fires. No "prepare X, commit Y" gap.
2. **Approval binds to the artifact.** Approving `draft-8821` authorizes sending *that* draft, once. It is not a standing grant to `send_email`.

This is why the split is worth two tools instead of one flag: it separates the deliberation the model is good at from the trigger the harness must control.

## Approval gates — always explicit human approval

These never proceed on model judgment alone, regardless of maturity level:

- Production deploy or any `deploy_or_runtime_change` against live.
- Any `external_communication` — a message a real third party receives.
- `delete_or_destructive` changes — dropping, overwriting, force-pushing, deleting branches/releases/tags.
- Permission, credential, or policy changes (`privileged_access`, `security_sensitive`).
- Financial or billing actions (`financial_or_billing`) — any spend or money movement.
- Exporting or moving `regulated_data` outside its compliance boundary.
- Irreversible migrations — schema/data changes without a clean rollback.
- Broad automated writes — a single action touching many records/files at once, even when each write alone is low-risk (blast radius, not per-item risk, sets the gate).

"Explicit approval" means a recorded human decision the harness stored outside the prompt, scoped to this action, and consulted by the gate before execution — not the model asserting it has approval.

## Safe defaults when uncertain

When risk classification is ambiguous or the environment is unknown, the harness fails toward the smaller blast radius:

- **draft over send**, **preview over apply**, **plan over execute**, **read over write**, **local validation over remote mutation**, **ask over act**.

An unclassifiable tool defaults to blocked, not to run. Uncertainty is resolved by producing a reviewable artifact and stopping — never by taking the irreversible path and hoping.

## The blocked result

When a gate denies an action, the tool does not error vaguely — it returns a structured, actionable observation the loop can act on. Illustrative:

```json
{
  "status": "blocked",
  "error_code": "approval_required",
  "details": {
    "tool": "deploy.commit",
    "risk_class": "deploy_or_runtime_change",
    "environment": "production",
    "artifact_ref": "deploy-plan-4f2a",
    "reason": "Production deploy requires explicit human approval."
  },
  "next_actions": [
    "Show the prepared plan (deploy-plan-4f2a) to the user for review.",
    "Request explicit approval, then re-invoke deploy.commit with the approval token."
  ]
}
```

The values are illustrative; the shape is the contract. `status: "blocked"` is distinct from `"failed"` — nothing went wrong, a gate is doing its job — and `next_actions` tells the model the only legitimate path forward (surface the artifact, obtain approval) instead of leaving it to retry blindly. See [tool-design](tool-design.md) for the full result/error/blocked envelope this conforms to.

## Sandboxing

Risky execution runs isolated from the model, never inside it. Shell, code execution, and untrusted-content processing run in containers or sandboxes with no ambient credentials; the model receives only the structured result. The harness — not the model — enforces user consent before a sandboxed run, command/domain allowlists on what the sandbox may touch, output truncation so a hostile result can't flood context, secret redaction on everything crossing back in, and logging of every invocation with its permission decision. The sandbox boundary is where prompt-injected instructions in tool output die: they land on data the harness treats as data, not on the permission engine.

## Kill switch

Every autonomous or long-running harness needs an **emergency stop that lives outside the agent process** — a control the model cannot see, reason about, or talk its way past. It revokes tool access and halts the loop immediately, mid-step; a stop the agent has to cooperate with is not a kill switch. Wire it to fire on both human command and automatic triggers: budget blown past a hard ceiling, error/denial rate spiking, a destructive action attempted outside policy, anomalous tool-call volume, or a tripped guardrail. On trip, freeze — don't let in-flight side effects continue — capture the trace, and surface an incident summary (what the agent was doing, which trigger fired, what state it left behind, what a human must check). The higher the maturity level, the less optional this is: at Level 4–5 it is a launch requirement, not a nice-to-have.
