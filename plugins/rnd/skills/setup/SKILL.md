---
name: setup
description: Set up the current folder as an RnD research workspace — index its Word, Excel, PowerPoint, PDF and Markdown files and configure Claude Code for cheap, precise work (Sonnet by default, RnD tools pre-approved). Use when starting a research project, after adding many files, or when the RnD tools seem broken.
argument-hint: "[folder] [--keep-model]"
model: haiku
allowed-tools: mcp__plugin_rnd_rnd__setup mcp__plugin_rnd_rnd__status Bash(uv --version) Bash(uv sync *)
---

Set up an RnD workspace. Arguments: `$ARGUMENTS` (optional folder, default: the current
working directory; `--keep-model` means do not change the folder's default model).

1. Call the RnD `setup` tool with `path` = the folder (use `"."` if none was given) and
   `keep_model: true` only if `--keep-model` was passed.
2. Report back in at most 8 lines:
   - workspace name and number of documents indexed, number of data tables;
   - any FAILED files or warnings (scanned PDFs without text, formulas without cached
     values) with what the user can do about each;
   - what changed in `.claude/settings.json` (default model → Sonnet; RnD read tools
     pre-approved) and that `CLAUDE.md` holds the grounding rules.
3. Finish with the next steps:
   - "Ask a question: `/rnd:ask …`  ·  numbers: `/rnd:analyze …`  ·  report: `/rnd:report …`"
   - "Restart Claude Code in this folder once so the new default model applies."
   - "New or changed files are re-indexed automatically when a session starts."

If the `setup` tool is not available (the RnD MCP server did not start):
1. Run `uv --version`. If uv is missing, tell the user to install it from
   https://docs.astral.sh/uv/getting-started/installation/ and stop.
2. Run `uv sync --project "${CLAUDE_PLUGIN_ROOT}/engine"` (first install takes about a
   minute), then ask the user to run `/mcp`, reconnect the `plugin:rnd:rnd` server and
   run `/rnd:setup` again.
