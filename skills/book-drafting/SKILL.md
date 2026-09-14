---
name: book-drafting
description: Draft, revise, or review chapters of the book "Agentic AI System Design: Building Reliable Systems That Act" against its editorial standard — chapter structure, evidence and citations, voice, diagrams, the book's analytical lenses, and the Google Docs revision workflow. Use when writing or editing a chapter, reviewing a chapter draft, addressing author comments in the manuscript, or producing chapter diagrams. Not for other books or general writing.
---

# Book Drafting: Agentic AI System Design

Editorial standard for every chapter iteration of *Agentic AI System Design: Building Reliable Systems That Act* (Arseny Kravchenko & team). Use it both to write and as the review checklist.

## 1. Chapter architecture

### Skeleton (non-negotiable)
1. **Opening hook**: a systems-level framing that demystifies hype in the first two sentences. Frame the chapter's central tension as a software engineering or distributed systems problem.
2. **`### This chapter covers`**: immediately after the hook; 4–6 numbered, high-signal statements of the engineering mechanisms discussed.
3. **~5 subchapters** (`X.1`–`X.5`). Do not fracture into 8+ micro-sections. Each subchapter needs enough mass to state an invariant, unpack the failure mode, and develop the architectural resolution.
4. **Closing principles**: an unnumbered list of 4–5 durable engineering truths that survive model and framework churn.

### Naturalized first principles
- No signposting: no `> **Load-bearing principle:**`, no "THIS IS IMPORTANT" callouts.
- Each subchapter is anchored by exactly one first principle, stated as the opening sentence and thesis of its prose.

## 2. Evidence and citations

- **No synthetic anecdotes.** Never invent teams or companies ("Imagine a team at ShopCorp..."). When a real production story is needed, leave a placeholder:
  `> **[Campfire story placeholder: Production outage caused by X mechanism under Y load]**`
- **Reference, don't retell.** Industry postmortems and case studies get 1–2 punchy paragraphs isolating the exact mechanism, then return to the design narrative.
- **Citation half-life.** 2023-era ML papers are often obsolete for frontier models; don't build chapters on them. Prefer:
  - timeless systems, database, and OS literature (Kleppmann, Saltzer & Schroeder, Lamport, compiler design);
  - concrete legal and regulatory precedents with binding rulings;
  - empirical benchmarks (SWE-bench, GAIA) cited for recovery dynamics or error distributions, never scoreboard cheering.

## 3. Voice

Arseny's register: dry, ironic, insider ML/systems engineer writing for senior practitioners. For line-level rewrites into this register, use the `tone-of-voice` skill if available.

- **Anti-hype**: translate agent magic into distributed systems, compiler feedback loops, and state machines.
- **Build-up → deflate**: acknowledge the academic or marketing promise, then deflate it with production failure modes.
- **Ugly-but-works**: prefer spartan, battle-tested solutions over baroque frameworks.
- **Asymmetric rule of thumb**: frontier models thrive on expressive primitives; smaller/distilled models need rigid guardrails and low branching factors.
- **Specifics over adjectives**: tokens, latencies, error codes, HTTP statuses, concurrency limits, dollars. A claim without a number, metric, or named tool gets grounded or cut.

Hard avoids:
- marketing/LinkedIn tone ("bridges the gap", "transformative journey", "seamlessly integrated", superlative stacks);
- pedagogical padding ("In this section, we will discuss...", "It is vital to understand...", "Let us delve into...");
- explaining the joke — keep ironies deadpan.

## 4. Diagrams

- **Concept-driven, text-light**: show boundaries, pipelines, layers, and spatial relationships prose can't convey quickly. No paragraphs or bullet lists inside boxes.
- **Unnumbered and uncoupled**: no "Figure 10.1" or phase tags inside the asset, so diagrams can be reordered across revisions.
- **Palette**: clean sans-serif, high contrast, subtle elevation; accents slate `#0f172a`, blue `#3b82f6`, green `#10b981`, red `#e11d48`.
- **Pipeline**: author as vector SVG → rasterize locally with `resvg_py` to high-DPI PNG (~480–500pt wide) → insert into the Google Doc at a unique text anchor placed where the image belongs, then remove the anchor text.

## 5. Analytical lenses

Every chapter, whatever the topic (memory, orchestration, planning, evals, tools, serving), examines its subject through these lenses:

1. **Untrusted remote worker.** An LLM is an untrusted, high-latency, nondeterministic remote worker with an unpredictable error profile — not a mind or collaborator. Use distributed systems vocabulary (consensus, partial failure, cache invalidation, state divergence, blast radius), not cognitive psychology.
2. **Baseline first.** Confront the non-agent baseline explicitly. If a state machine, hardcoded DAG, SQL query, or single prompt gets 99% reliability at 1/10th the cost, why an agent? Autonomy is an expensive probabilistic fallback, not a design goal.
3. **Boundary of guarantees.** Map where probabilistic reasoning stops: the model interprets, explores, drafts, hypothesizes; the runtime authorizes, validates, bounds, enforces, audits. A design that relies on the model to enforce its own safety, stopping criteria, privacy, or transactional consistency is broken.
4. **Failure-driven architecture.** Start each pattern from a concrete production failure (context rot, state divergence, error cascades, deadlock, runaway spend) and derive the minimal deterministic defense that detects, isolates, and recovers from it. Never from happy-path demos.
5. **Compounding errors and token economics.** Ground multi-step workflows in $P = p^n$: at 95% per step, a 10-turn loop succeeds ~60% of the time ($0.95^{10} \approx 0.60$). Without checkpoints, verification gates, or rollbacks, loops collapse exponentially. Ignoring turn count, latency budgets, and token cost makes it a toy demo.
6. **Spartan over baroque.** Puncture hype around monolithic frameworks, multi-agent simulations, and loops with dozens of moving parts. Champion explicit state machines, transparent event logs, standard protocols, modular interfaces — "spartan solutions with duct tape as the key ingredient".

## 6. Revision workflow

### Author notes vs. AI drafts
Drafts often mix the author's shorthand notes with verbose AI text. Identify the author's specific insights and architectural opinions and preserve them fiercely; polish phrasing and structure, but never over-prune subtle technical stances.

### Google Docs
The manuscript lives in Google Docs. Use the `gdoc` skill for all document operations and follow its safety rules; the book adds these requirements:

- **Sync before editing**: re-read the chapter immediately before each change so revision state is current and collaborator edits aren't clobbered.
- **Surgical edits, never blind rewrites**: targeted `gdoc edit` replacements (file-backed old/new text for long passages) preserve comment threads, suggested edits, and embedded images. Do not `gdoc write` a chapter.
- **Close the feedback loop**: when addressing an inline author comment, reply in that comment thread describing the change.
