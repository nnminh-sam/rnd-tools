---
name: report
description: Produce a verified R&D report or memo as Word (default) or PDF — evidence gathered in parallel on Haiku, numbers computed exactly on Sonnet, drafted and rendered on Sonnet, every citation checked. Use for status reports, test summaries, research write-ups, competitor or market reviews.
argument-hint: "<topic> [--pdf] [--for <audience>] [--audit]"
model: sonnet
effort: medium
---

Produce a verified report on: **$ARGUMENTS**

You are orchestrating on Sonnet. Do not read documents or write files yourself — delegate
and keep your own context small.

**Running agents** — follow exactly:
- Call the Agent tool with `run_in_background: false` every time; for parallel steps put
  several Agent calls in one message. A background agent reports back after this command
  has ended, and the follow-up then runs on the session's model (often Opus).
- Give agents absolute paths: packs in `${CLAUDE_PROJECT_DIR}/.rnd/packs/`, drafts in
  `${CLAUDE_PROJECT_DIR}/outputs/`. File names never start with analysis, report, summary or
  findings — Claude Code blocks agents from writing such files.
- Agents write and verify their own files. If one reports a failed write or verify,
  launch it again with the error message; never fix its files yourself.

1. **Scope.** Title, audience (default: project team), format (`docx`; `pdf` with
   `--pdf`), a file slug naming the subject (e.g. `p2-test-status`), and 2–4 evidence
   themes. Ask the user only if the topic is genuinely ambiguous.
2. **Gather in parallel** (one message):
   - one `rnd:librarian` per theme: "Build an evidence pack on '<theme>' for a report on
     '<topic>'. Write ${CLAUDE_PROJECT_DIR}/.rnd/packs/<slug>-<theme>.md. Return path, summary, gaps."
   - if the report needs figures, one `rnd:analyst`: "Compute: <explicit list — include
     every count the summary will state, e.g. how many targets pass, how many
     configurations meet both limits>. Write ${CLAUDE_PROJECT_DIR}/outputs/figures-<slug>.md. Return calc
     ids and the answer section."
3. **Write.** `rnd:writer` with title, audience, format, pack paths, the figures path and
   calc ids: "write ${CLAUDE_PROJECT_DIR}/outputs/<slug>.md in the report structure, verify, render to
   <format>".
4. **Audit** when `--audit` is given or the audience is outside the project team
   (steering committee, management, customers): `rnd:auditor` on `outputs/<slug>.md`.
   If it reports problems, `rnd:writer` again with the audit findings: "fix these in
   ${CLAUDE_PROJECT_DIR}/outputs/<slug>.md, verify, re-render".
5. **Reply** with: the output file path, the verification line, a 3-bullet summary with
   citations, what the audit found and fixed (if run), and the evidence gaps.
