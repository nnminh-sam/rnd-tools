---
name: show
description: Show the exact source behind a citation such as [@doc-id#anchor] or [@calc:N] — the file, the location in plain words (page, slide, table row, sheet cells) and the verbatim text or SQL result. Use when the user wants to check, open or trust a cited fact.
argument-hint: "<citation(s), e.g. kickoff#t1.r3 or calc:5>"
model: haiku
allowed-tools: mcp__plugin_rnd_rnd__read
---

Show the sources for: `$ARGUMENTS`

1. Call the RnD `read` tool once with every ref in the arguments (it accepts
   `[@doc#anchor]`, `doc#anchor` and `calc:N`; drop any quoted words after the ref).
2. Print each result exactly as returned, inside a code block — do not summarise or
   reformat it. The first line names the file and the location in plain words.
3. After the block, one line per ref telling the user where to look in the original,
   e.g. "Open `sources/meetings/2026-02-09 Kickoff - Project KESTREL.docx` → table 1,
   row 3", or for a calc: "SQL result saved in `.rnd/calcs/5.json`".
