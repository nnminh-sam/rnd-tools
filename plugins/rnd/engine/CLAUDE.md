# KESTREL — RnD workspace

This folder is an RnD research workspace. Sources live in `sources/` and `notes/`; generated work goes to `outputs/`.

Rules for every answer and document produced here:
- Use the RnD tools (search / read / outline / tables / sql) to get facts. Never open .docx/.xlsx/.pptx/.pdf with Read.
- Every factual statement carries a citation: `[@doc-id#anchor]`, or `[@calc:N]` for numbers computed with the sql tool.
- Quote verbatim when quoting: `[@doc-id#anchor "exact words"]`. Do not do arithmetic in your head — use sql.
- Anything not backed by a source must be labelled `Assumption:`, `Hypothesis:` or `Idea:`. If evidence is missing, say so.
- Run verify on any Markdown you write to `outputs/` before rendering it to Word/PowerPoint/PDF.
- Commands: /rnd:ask, /rnd:analyze, /rnd:brainstorm, /rnd:report, /rnd:deck, /rnd:decide, /rnd:capture, /rnd:help.
