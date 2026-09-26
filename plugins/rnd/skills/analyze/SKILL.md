---
name: analyze
description: Answer a quantitative question with exact SQL over the workspace's Excel sheets, CSVs and document tables (runs on Sonnet). Every figure is a saved, citable calc; can export results to Excel with a chart. Use for averages, totals, counts, comparisons, rankings, what-if configurations, pass/fail against targets.
argument-hint: "<question> [--xlsx]"
context: fork
agent: rnd:analyst
model: sonnet
background: false
---

Answer this quantitative question from the RnD workspace data:

> $ARGUMENTS

1. Call `status` first: it confirms the workspace root (normally `${CLAUDE_PROJECT_DIR}`).
   Write files only under it, with absolute paths — never relative to this skill's base
   directory.
2. `tables` → probe (`save: false`) → compute in SQL → sanity-check. Every number in your
   answer comes from a saved calc (`[@calc:N]`); do no arithmetic yourself — put deltas,
   margins, pass/fail flags and counts ("how many pass") in the SQL.
3. Targets or thresholds from documents are looked up (`search`/`read`) and cited at the
   exact row, not assumed.
4. Write `<root>/outputs/figures-<short-slug>.md` (Answer / Details / Method / Caveats),
   e.g. `${CLAUDE_PROJECT_DIR}/outputs/figures-shell-fatigue.md`.
   Do not start the file name with analysis, report, summary or findings — Claude Code
   refuses to let agents write such files. The verifier hook checks the file; fix every
   error. Give each table a caption line ending in its calc, e.g.
   `Cost per configuration [@calc:5]:`, or a Source column.
5. If `--xlsx` was given (or a spreadsheet/chart was asked for), call `export_xlsx` with
   the calc ids, `out: "outputs/figures-<short-slug>.xlsx"` and a suitable chart type.

Return: the Answer section with its citations (keep wide tables in the file, not in the
reply), the calc ids, and the output path(s).
