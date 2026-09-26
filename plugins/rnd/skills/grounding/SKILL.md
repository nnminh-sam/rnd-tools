---
name: grounding
description: Rules for answering from an RnD workspace (a folder with .rnd/) — how to get facts from Word/Excel/PowerPoint/PDF files cheaply and exactly, how to cite, and when to delegate to the RnD agents. Load whenever the user asks about project documents, data or research without using an /rnd command.
user-invocable: false
---

# Working in an RnD workspace

**Get facts through the RnD tools, not by opening files.**
- `search` (pass 2–5 phrasings) → `read` the refs → cite. `outline` shows a document's
  anchors. `mode: "exact"` finds codes, names and figures.
- Never use Read on .docx/.xlsx/.pptx/.pdf (a hook blocks it): it loads the whole file
  and loses structure. `read` returns the exact text of just the part you need.
- Numbers: `tables` → `sql` (DuckDB). The result is saved as `calc:N`. Do no arithmetic
  yourself — put differences, ratios and percentages in the SQL.

**Delegate by default** (cheaper and keeps your context small):
- facts/quotes → `rnd:librarian` (Haiku) · numbers → `rnd:analyst` (Sonnet)
- documents → `rnd:writer` · ideas → `rnd:ideator` · web → `rnd:scout`
- judgement over a pack → `rnd:strategist` (Opus) · fact-check → `rnd:auditor`
- launch them with `run_in_background: false`, give them absolute paths
  (`<workspace>/.rnd/packs/`, `<workspace>/outputs/`), and let them write their own
  files. Never name a Markdown file `analysis-…`, `report-…`, `summary-…` or
  `findings-…`: Claude Code blocks agents from writing those.

**Cite everything** — a deterministic verifier checks it:
- `[@doc-id#anchor]` after the claim; `[@doc-id#anchor "verbatim quote"]` for quotes;
  `[@calc:N]` for computed figures; several: `[@a#p3; @calc:4]`.
- A figure must appear in its cited source at the precision written ("about 150,000"
  may round 148,250; a bare "150,000" may not).
- Speculation is fine when labelled: `Assumption:`, `Hypothesis:`, `Idea:`,
  `Recommendation:`; tables of scores get "(judgement)" in a header cell.
- If the workspace lacks the evidence, say so — never fill gaps from general knowledge
  without labelling it as such.

**Write, verify, render:** draft Markdown in `outputs/`, the hook verifies on save, then
`render` to docx/pptx/pdf (refused while verification fails) or `export_xlsx` for calcs.
Tables: put the calc/ref in a Source column, or in a caption line right above the table
(`Cost per option [@calc:5]:`). Counts across rows ("five of eight pass") come from a
calc too — the verifier checks them. Users check any citation with `/rnd:show <ref>`.
