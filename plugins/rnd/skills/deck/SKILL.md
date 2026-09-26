---
name: deck
description: Build a verified PowerPoint deck (native tables and editable charts from exact calcs, speaker notes, automatic sources slides). Evidence on Haiku, numbers and writing on Sonnet. Use for design reviews, steering-committee updates, test-result readouts, pitch of a concept.
argument-hint: "<topic> [--slides N] [--template file.pptx] [--for <audience>]"
model: sonnet
effort: medium
---

Build a verified slide deck on: **$ARGUMENTS**

You are orchestrating on Sonnet. Do not read documents or write files yourself.

**Running agents** — follow exactly:
- Call the Agent tool with `run_in_background: false` every time; for parallel steps put
  several Agent calls in one message. A background agent reports back after this command
  has ended, and the follow-up then runs on the session's model (often Opus).
- Give agents absolute paths: packs in `${CLAUDE_PROJECT_DIR}/.rnd/packs/`, drafts in
  `${CLAUDE_PROJECT_DIR}/outputs/`. File names never start with analysis, report, summary or
  findings — Claude Code blocks agents from writing such files.
- Agents write and verify their own files. If one reports a failed write or verify,
  launch it again with the error message; never fix its files yourself.

1. **Scope.** Audience (default: project team), length (default 6–9 slides), template
   (`--template` path, optional), a file slug. Draft a one-line storyline: what should
   the audience decide or believe after the last slide? Reuse existing packs in
   `.rnd/packs/` and memos in `outputs/` on the same subject if there are any (mention
   them to the agents instead of re-gathering).
2. **Gather in parallel** (one message): `rnd:librarian` packs for the 2–3 themes of the
   storyline that are not covered yet, and one `rnd:analyst` for every figure or chart
   ("compute <figures>; one calc per chart, with clear column aliases; write
   ${CLAUDE_PROJECT_DIR}/outputs/figures-<slug>.md").
3. **Write.** `rnd:writer` with the storyline, audience, slide budget, pack and memo
   paths, calc ids, template, and "write ${CLAUDE_PROJECT_DIR}/outputs/<slug>-deck.md in the deck
   structure (takeaway titles, ≤ 6 bullets, charts from calcs, notes), verify, render to
   pptx".
4. **Reply** with the .pptx path, the verification line, and the slide titles in order.
