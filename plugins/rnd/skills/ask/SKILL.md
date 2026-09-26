---
name: ask
description: Answer a question from the workspace documents with verified citations the user can check with /rnd:show. Runs on Haiku in an isolated context, so it is the cheapest way to get facts out of project reports, interviews, test data, meeting notes and decks. Use for what/which/when/why/how-many questions about the project.
argument-hint: "<question>"
context: fork
agent: rnd:librarian
model: haiku
background: false
---

Answer this question from the RnD workspace, using only indexed evidence:

> $ARGUMENTS

1. Call `status` first: it confirms the workspace root (normally `${CLAUDE_PROJECT_DIR}`)
   and the absolute folder for answers. Write files only there, with absolute paths —
   never relative to this skill's base directory.
2. **Reuse.** If `…/.rnd/packs/answer-<short-slug>.md` exists, its `question:` line asks
   the same thing and status says the index is up to date, run `verify` on it and return
   it instead of searching again.
3. **Find.** Plan the facts needed, `search` with 3–5 phrasings per fact, `read` the refs.
   Counts, averages and totals go through `tables` → `sql` (cite `[@calc:N]`).
4. **Write** `…/.rnd/packs/answer-<short-slug>.md`:
   ```markdown
   ---
   question: <the question as asked>
   ---
   - <most important fact> [@doc-id#anchor]
   - <next fact> [@doc-id#anchor "short verbatim quote"]

   ## Gaps
   - <what the workspace does not say> (searched: "…", "…")
   ```
   2–10 bullets, one fact per citation, each citation at the most specific anchor that
   holds the fact — a table row (`#t1.r3`), a paragraph (`#p14`), a page (`#page2`), a
   sheet row (`#Quotes!A8:O8`) — never a whole table or a range of many blocks.
5. The verifier hook checks the file on every write: fix every error and every
   `broad-ref` warning. Figures must appear in the cited source exactly as written.
6. If the question is ambiguous, answer the most likely reading, say which reading you
   used in the first bullet (`Assumption: …`), and list other readings under Gaps.

Return: the verified answer (bullets with their citations), the file path, and the line
"Check any source with `/rnd:show <ref>`." If the workspace has no evidence for the
question, say so plainly and list what you searched.
