---
name: brainstorm
description: Grounded brainstorming — gathers the relevant evidence (constraints, user needs, test results) on Haiku, then generates, scores and shortlists ideas on Sonnet, with every idea linked to its evidence and every assumption labelled. Use for ideation, concept generation, fixing a failed design, exploring options.
argument-hint: "<topic or problem>"
model: sonnet
effort: medium
---

Run a grounded brainstorm on: **$ARGUMENTS**

You are orchestrating on Sonnet. Do not read documents or write files yourself.

**Running agents** — follow exactly:
- Call the Agent tool with `run_in_background: false` every time. A background agent
  reports back after this command has ended, and the follow-up then runs on the
  session's model (often Opus) instead of Sonnet.
- Give agents absolute paths: packs in `${CLAUDE_PROJECT_DIR}/.rnd/packs/`, drafts in
  `${CLAUDE_PROJECT_DIR}/outputs/`. File names never start with analysis, report, summary or
  findings — Claude Code blocks agents from writing such files.
- Agents write and verify their own files. If one reports a failed write or verify,
  launch it again with the error message; never fix its files yourself.

1. `rnd:librarian`: "Build an evidence pack for brainstorming '<topic>': the problem and
   its root causes, hard constraints and targets (cost, materials, dates, test targets),
   user needs with verbatim quotes, relevant test results, and ideas already recorded in
   notes. Write ${CLAUDE_PROJECT_DIR}/.rnd/packs/brainstorm-<slug>.md. Return the path, a short summary
   and gaps."
2. `rnd:ideator`: the topic, the pack path, and "generate, ground, score and shortlist
   ideas; write ${CLAUDE_PROJECT_DIR}/outputs/brainstorm-<slug>.md".
3. Reply with the shortlist (keep the citations), the file path, the evidence gaps, and
   one line suggesting the next step (`/rnd:decide …` to choose, `/rnd:deck …` to present).
