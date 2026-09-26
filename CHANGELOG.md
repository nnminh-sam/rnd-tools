# Changelog

## 0.2.1 — 2026-09-26

- Install from GitHub: `claude plugin marketplace add nnminh-sam/rnd-tools`, then
  `claude plugin install rnd@rnd-tools` (README: install, update, team sharing).
- `plugin.json` gains `homepage` and `repository`; the marketplace owner is `nnminh-sam`.
- The engine starts with `uv run --frozen --no-dev`, so users' installs skip pytest/ruff.
- Removed a stray workspace `CLAUDE.md` and `.claude/settings.json` that had been
  committed inside `plugins/rnd/engine/` and shipped with the plugin.

## 0.2.0 — 2026-09-26

Fixes from the first live test (a user on Opus running the tutorial). Same lessons from an
Opus session, before (estimated from the transcript) → after (`claude -p` total):
`/rnd:ask` about $1.10 → $0.04, `/rnd:analyze` about $1.25 → $0.25, `/rnd:brainstorm`
about $1.40 → $0.78 with no Opus at all.

Model routing
- Forked skills named their agent `librarian`/`analyst`/`scout`; plugin agents are
  `rnd:<name>`, so Claude Code fell back to `general-purpose` on the session model (Opus).
  They now name `rnd:<name>` and pin `model:` too.
- Orchestrating skills launched agents in the background; each "agent finished" turn then
  ran on the session model. Agents now run in the foreground (`run_in_background: false`),
  so the whole command stays on Sonnet.
- The prompt hook no longer fires on background-agent notifications, and warns once when a
  session was switched to Opus mid-way (SessionStart could not see a later `/model`).

Files and paths
- Claude Code blocks agents from writing `.md` files whose name starts with analysis,
  report, summary or findings. The analyst now writes `outputs/figures-<slug>.md`;
  the Excel export defaults to `figures.xlsx`.
- Skills give agents absolute paths via `${CLAUDE_PROJECT_DIR}`; `status` prints the
  write locations; `verify` refuses files outside the workspace; the post-write hook blocks
  drafts written outside the workspace or into a stray `outputs/.rnd/`.
- A workspace is now marked by `.rnd/config.json`, not any `.rnd/` folder.
- Exported Claude Code conversations (`/export` files) are never indexed: agents could
  otherwise cite earlier chat answers as evidence.

Precision
- Verifier: dates are one figure (`9 February 2026` = `2026-02-09`) and a document's own
  date (title/file name) counts as evidence; spelled-out counts are checked ("six of
  eight"); table rows inherit the citation of the header row or of a caption line right
  above the table; `calc:N` is a label, not a figure; SQL thresholds count as calc
  evidence; a missing index is one error, not one per citation; new `broad-ref` warning
  for citations spanning more than 10 blocks.
- Search hits name the exact blocks to cite (`cite: doc#t1.r10`) instead of chunk ranges.
- MCP tools now return the engine's error message (the SDK hid it: agents only saw
  "Error executing tool sql", and never learned why `render` refused).
- `read` shows the location in words ("table 1, row 3") and opens `calc:N`.
- PDF tables: words split by cell wrapping are rejoined ("Statu s" → "Status").

Commands and docs
- New `/rnd:show <ref>`: the verbatim source behind any citation.
- Tutorial rewritten: 12 lessons with what happens, exact expected answers, how to check
  them, time and troubleshooting. Fixed expectations: P2 baseline + EcoLine also meets both
  targets (three configurations, not two); manual edits need `/rnd:verify`.
- Static tests for the plugin layer (agent names, foreground agents, blocked file names).

## 0.1.0 — 2026-09-25

First release.

- Engine: extraction for docx/xlsx/pptx/pdf/md/txt/csv/html with stable anchors; SQLite FTS5
  index with multi-query fusion and per-document diversification; optional semantic search;
  DuckDB tables from every sheet/CSV/document table; saved, citable calcs.
- Citation verifier (refs, verbatim quotes, figure matching at written precision, uncited
  figures) gating all rendering.
- Renderers: Markdown → docx / pdf / pptx (native charts, notes, sources slides); calcs → xlsx
  with charts and provenance. Surgical xlsx/docx edits. Verbatim web capture.
- Claude Code plugin: 11 commands, 7 model-pinned agents, hooks for read guarding,
  auto-verification, session briefing and prompt routing; MCP server with 14 tools.
- KESTREL demo workspace, tutorial with expected answers, eval suite.
