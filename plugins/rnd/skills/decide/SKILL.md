---
name: decide
description: Decision support with premium reasoning used only where it pays — Haiku gathers a verified evidence pack, Sonnet computes the option figures exactly, then Opus reasons over that compact pack to recommend, with explicit trade-offs, confidence, risks and evidence gaps. Use for go/no-go, option selection, trade-offs, root-cause conclusions.
argument-hint: "<decision question>"
model: sonnet
effort: medium
---

Support this decision: **$ARGUMENTS**

You are orchestrating on Sonnet. Do not read documents, write files or reason about the
answer yourself — the strategist does the reasoning.

**Running agents** — follow exactly:
- Call the Agent tool with `run_in_background: false` every time; for parallel steps put
  several Agent calls in one message. A background agent reports back after this command
  has ended, and the follow-up then runs on the session's model (often Opus).
- Give agents absolute paths: packs in `${CLAUDE_PROJECT_DIR}/.rnd/packs/`, drafts in
  `${CLAUDE_PROJECT_DIR}/outputs/`. File names never start with analysis, report, summary or
  findings — Claude Code blocks agents from writing such files.
- Agents write and verify their own files. If one reports a failed write or verify,
  launch it again with the error message; never fix its files yourself.

1. **Evidence and numbers, in parallel** (one message):
   - `rnd:librarian`: "Build an evidence pack for the decision '<question>': the options
     and what each involves, decision criteria and targets, test/engineering evidence per
     option, cost/schedule facts, stakeholder positions (with quotes), and prior
     decisions (quote them exactly). Write ${CLAUDE_PROJECT_DIR}/.rnd/packs/decide-<slug>.md. Return
     path, summary, gaps."
   - `rnd:analyst` (skip only if the decision is purely qualitative): "For the options in
     '<question>', compute every figure a comparison needs — per option and per
     combination: cost, deltas and margins vs target, performance vs target, and counts
     such as how many options meet all limits. Write
     ${CLAUDE_PROJECT_DIR}/outputs/figures-decide-<slug>.md. Return calc ids."
2. **Reason.** `rnd:strategist` with the question, the pack path, the figures path and
   calc ids: "Write ${CLAUDE_PROJECT_DIR}/outputs/decision-<slug>.md."
3. **Audit.** `rnd:auditor` on `${CLAUDE_PROJECT_DIR}/outputs/decision-<slug>.md`. If it finds
   OVERSTATED / UNSUPPORTED / MISATTRIBUTED claims, `rnd:strategist` again with the audit
   findings: "correct these in ${CLAUDE_PROJECT_DIR}/outputs/decision-<slug>.md and re-verify".
4. **Reply** with: the recommendation line and confidence, the top 3 cited reasons, the
   main risk, the evidence gaps, what the audit changed, and the memo path. Offer
   `/rnd:deck` to present it.
