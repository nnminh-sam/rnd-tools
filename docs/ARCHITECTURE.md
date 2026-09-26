# Architecture

RnD has two halves with a hard boundary between them:

- **The engine** (`plugins/rnd/engine`, Python package `rnd`) is deterministic and
  model-free. It extracts, indexes, searches, computes, verifies and renders. Same input,
  same output, every time. No API keys.
- **The Claude Code layer** (skills, agents, hooks) supplies the intelligence: planning,
  query expansion, reading, writing, judgement. It reaches the engine only through the
  MCP tools, and its output is checked by the engine's verifier.

This split is what makes the toolset both cheap and trustworthy: models never re-type
source documents or compute figures, and everything they claim is checkable.

## Components

```
                        Claude Code session
 ┌───────────────────────────────────────────────────────────────────────┐
 │ skills/ (/rnd:*)   agents/ (model-pinned)        hooks/hooks.json     │
 │  ask ──fork──▶ librarian (haiku)                 PreToolUse Read      │
 │  analyze ─fork▶ analyst (sonnet)                   → deny Office reads│
 │  report/deck/brainstorm/decide (sonnet)          PostToolUse Write|Edit│
 │    └─▶ librarian, analyst, writer, ideator,        → verify outputs/*.md│
 │        strategist (opus), auditor (haiku)        SessionStart          │
 │  capture ─fork▶ scout (haiku)                      → briefing, reindex │
 │                                                  UserPromptSubmit      │
 │                                                    → route to /rnd:*   │
 └──────────────┬─────────────────────────────────────────┬──────────────┘
                │ MCP (stdio): mcp__plugin_rnd_rnd__*      │ rnd-hook <event>
 ┌──────────────▼─────────────────────────────────────────▼──────────────┐
 │ engine: rnd.mcp_server / rnd.hooks / rnd.cli  →  rnd.api (services)   │
 │  extract/  word excel powerpoint pdf text   → Blocks + Tables         │
 │  index/    store (SQLite+FTS5) indexer search vectors(optional)       │
 │  data/     tables (DuckDB, calcs)                                     │
 │  verify.py cite.py  (citation contract)                               │
 │  render/   model(Markdown) word slides pdf sheets                     │
 │  edit.py capture.py setup.py                                          │
 └───────────────────────────────┬───────────────────────────────────────┘
                                 ▼
          <workspace>/.rnd/  index.sqlite · data.duckdb · calcs/ · packs/ · config.json
```

## Data model

**Workspace** — any folder with `.rnd/config.json` (found by walking up from the cwd,
like `.git`; a bare `.rnd/` folder is not enough, so a stray `outputs/.rnd/` is never
mistaken for one). Sources are read-only to the indexer; derived state lives in `.rnd/`.

**Document** — one indexed file, with a stable, readable `doc_id` derived from its file
name (`TR-2026-031 P2 prototype test report.pdf` → `tr-2026-031-p2-prototype-test-report`).

**Block** — the atomic unit of extracted text, with an **anchor** a person can find in the
original file:

| Type | Anchors |
|---|---|
| docx | `p12` (12th non-empty paragraph), `t2.r3` (table 2 row 3) |
| xlsx | `Sheet!A5:H5` (a row), `'Sheet name'!A5:H5`; the sheet summary is `Sheet!A1:H30` |
| pptx | `s5` (slide text), `s5.t1` (table), `s5.c1` (chart data), `s5.notes` |
| pdf | `page3`, or `page3.1`, `page3.2` for long pages |
| md/txt/html | `L10-L14` (line range) |
| csv | `R7` (line 7) |

A ref is `doc_id#anchor`. Resolution (`Store.resolve`) also accepts ranges (`p12-p18`,
`L3-L40`), parents (`s5` → the slide and its tables/notes; `t2` → all rows), and any cell
or range inside a sheet (`Quotes!C14` → the row containing it).

**Chunk** — a retrieval unit of consecutive blocks within one section/slide/page/sheet,
indexed in FTS5 (porter stemming + diacritic folding, so Vietnamese text matches with or
without accents). A hit's ref spans the chunk (`kickoff#p14-t1.r12`); search also names
the blocks inside it that match the query (`cite: kickoff#t1.r10`), which is what agents
cite.

**Table** — every sheet, CSV and table found in Word/PowerPoint/PDF (and chart data in
PowerPoint) becomes a DuckDB table named `<doc_id>__<table>` in snake_case. Header rows
are detected below title rows; placeholder values like `n/a` become NULL and are reported.

**Calc** — the saved result of an `sql` call (`.rnd/calcs/N.json`: SQL, full-precision
rows, source tables and files). Cited as `[@calc:N]`.

## The citation contract

Implemented in `cite.py` (syntax) and `verify.py` (checks):

```
[@doc-id#anchor]                    location
[@doc-id#anchor "exact words"]      location + verbatim quote
[@calc:7]                           saved SQL result
[@a#p3; @calc:7]                    several sources
```

For each Markdown file the verifier checks, per statement (paragraph, list item, table
row) and per sentence:

1. every ref resolves (**error** `unknown-ref`);
2. quotes appear verbatim, modulo whitespace/quote-style/case, `…` allowed (**error** `bad-quote`);
3. every figure in a cited sentence appears in the cited evidence at the precision written:
   `148,233` ↔ 148233.33 · `46.81%` ↔ 0.4681 · `148k` or "about 150,000" ↔ 148,250, but a
   bare `150,000` does not match 148,250 (**error** `figure-mismatch`). Dates are one
   figure (`9 February 2026` ↔ `2026-02-09`, and a document's own date in its title or
   file name counts as evidence); counts in words are figures ("six of eight"); numbers
   in a calc's SQL (thresholds) count as that calc's evidence;
4. no sentence states a figure without a citation (**error** `uncited-figure`);
5. overall citation coverage, and refs spanning more than 10 blocks (**warnings**
   `low-coverage`, `broad-ref`).

A table row without its own citation is checked against the citation in the table's
header row, or on the heading/caption line directly above the table
(`Results [@calc:8]:`). `verify` refuses files outside the workspace.

Exempt, but counted: statements starting `Assumption:`, `Hypothesis:`, `Idea:`,
`Recommendation:`, `Risk:`…; tables whose header contains `(judgement)`; sections titled
Sources / References / Gaps. Labels such as "Table 2", "Step 3", "Top 5", part numbers
(`KS-204`) and product names (`P2`) are never treated as figures.

The verifier is stdlib-only (plus the SQLite index), so the post-write hook runs in well
under a second. `render` calls it and refuses to write Office files on errors.

## Model routing

| Role | Agent | Model | Sees |
|---|---|---|---|
| Find & quote evidence | `librarian` | haiku | search snippets, read excerpts |
| Numbers | `analyst` | sonnet (effort medium) | table schemas, SQL results |
| Write reports/decks | `writer` | sonnet (effort medium) | evidence packs, calcs |
| Ideas | `ideator` | sonnet (effort medium) | evidence packs |
| Web sources | `scout` | haiku | search results, captured pages |
| Judgement | `strategist` | opus (effort high) | only the evidence pack + calcs |
| Fact-check | `auditor` | haiku | claims paired with evidence |

Skills that orchestrate several agents (`report`, `deck`, `brainstorm`, `decide`) set
`model: sonnet` in their frontmatter, which switches the main session to Sonnet for that
turn — so even a user whose default is Opus orchestrates on Sonnet. That only holds while
the turn lasts, so these skills launch every agent with `run_in_background: false`
(parallel = several Agent calls in one message): a background agent would report back in
a *new* turn, which runs on the session model. Single-agent skills (`ask`, `analyze`,
`capture`) use `context: fork` + `agent: rnd:<name>` + `model:` and run entirely in the
pinned subagent, returning only the verified result to the main conversation.

`/rnd:setup` also writes `"model": "sonnet"` into the workspace's
`.claude/settings.json`, so everyday chat in a research folder defaults to Sonnet.

## Hooks

| Event | Handler | Purpose |
|---|---|---|
| PreToolUse `Read` on .pdf/.docx/.xlsx/.pptx… | `pre-read` | deny, and name the doc id + the RnD tool to use |
| PostToolUse `Write`/`Edit` on `*.md` | `post-write` | verify files in `outputs/` and `.rnd/packs/`; block with the issues on FAIL; block drafts written outside the workspace or into a stray `.rnd/` |
| SessionStart | `session-start` | one-paragraph briefing; on Opus, tell Claude to delegate and tell the user the price difference |
| SessionStart (async) | `session-index` | re-index changed files in the background |
| UserPromptSubmit | `prompt` | routing hint for free-form requests (max 3 visible tips per session); one-time notice if the session was switched to Opus; ignores harness messages such as `<task-notification>` |

All hooks are silent outside RnD workspaces and never fail the session (errors go to
stderr, exit code 0).

## Design decisions

- **MCP as the interface** (not Bash): structured arguments, no shell quoting, per-tool
  permissions, works the same on macOS/Windows/Linux. The CLI mirrors every tool for humans
  and scripts.
- **SQLite FTS5 by default, embeddings optional**: exact-term search is what precision work
  needs (part numbers, test IDs, figures); the librarian supplies synonyms. Semantic
  search (`fastembed`, multilingual MiniLM) can be switched on per workspace.
- **Markdown as the intermediate format**: cheap for models to write, diffable, verifiable;
  renderers are deterministic.
- **Edits write new files by default** (`name.edited.xlsx`) and refuse lossy in-place
  rewrites of workbooks that contain charts/images.
- **The demo is generated** (`engine/tools/build_demo.py`) from one data section, together
  with the golden facts used by tests and the tutorial's expected answers.
