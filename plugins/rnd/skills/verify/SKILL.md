---
name: verify
description: Check a Markdown report, memo or deck source — every citation resolves, quotes are verbatim, every figure matches its source, nothing numeric is uncited. With --deep, also runs a semantic audit (does the source really say it?). Use before sharing any document.
argument-hint: "[outputs/file.md] [--deep]"
model: haiku
allowed-tools: mcp__plugin_rnd_rnd__verify Glob
---

Verify: `$ARGUMENTS`

1. Determine the file: the path given, otherwise the most recently modified `.md` in
   `outputs/` (use Glob).
2. Call the RnD `verify` tool on it and show the result block as-is.
3. If `--deep` was given, launch the `rnd:auditor` agent on the file with
   `run_in_background: false`, and show its audit.
4. End with one line: "Ready to share" (PASS and no audit problems), or the number of
   issues to fix and the suggestion to ask Claude to fix them (the fixes are mechanical:
   correct figure, verbatim quote, add citation, or label as Assumption/Hypothesis).
   Remind the user that editing a file by hand is not checked automatically — run
   `/rnd:verify <file>` again after manual edits.
