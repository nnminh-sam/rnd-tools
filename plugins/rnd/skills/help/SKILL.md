---
name: help
description: Explain the RnD toolset and recommend the right command and model for what the user wants to do (questions, analysis, reports, decks, brainstorming, decisions, web research), including what each costs. Use when the user asks how to use RnD, which command to use, or why a model was chosen.
argument-hint: "[what you want to do]"
model: haiku
---

The user asked: `$ARGUMENTS`

If the question is specific, answer it in a few lines and recommend one command with a
concrete example invocation for their goal. Otherwise print this guide (adapt examples to
the current workspace if you know its topic):

| You want to… | Command | Models used |
|---|---|---|
| Get a fact, quote or short answer | `/rnd:ask <question>` | Haiku |
| Numbers: averages, totals, comparisons, what-ifs | `/rnd:analyze <question> [--xlsx]` | Sonnet + SQL |
| Ideas for a problem | `/rnd:brainstorm <topic>` | Haiku → Sonnet |
| A Word/PDF report | `/rnd:report <topic> [--pdf]` | Haiku → Sonnet |
| A PowerPoint deck | `/rnd:deck <topic>` | Haiku → Sonnet |
| A decision / trade-off | `/rnd:decide <question>` | Haiku → Sonnet → **Opus** (on a small pack) |
| Evidence from the web | `/rnd:capture <urls or topic>` | Haiku |
| See the source behind a citation | `/rnd:show <ref>` | Haiku |
| Check a document before sharing | `/rnd:verify [file] [--deep]` | no model (+ Haiku with --deep) |
| Index a new folder / fix setup | `/rnd:setup` | Haiku |
| Learn with a realistic project | `/rnd:tutorial` | Haiku |

List prices per million tokens (input/output): Haiku 4.5 $1/$5, Sonnet 5 $2/$10, Opus 5.5
$4/$20 — so Haiku is a quarter and Sonnet half of Opus per token. The bigger saving is
volume: agents read small cited snippets instead of whole files, and Opus only ever sees
a compact evidence pack. To see what a task really cost, run `/cost` after it (or
`claude -p … --output-format json` and read `total_cost_usd`).

Why it is cheap **and** precise:
- The engine extracts documents deterministically; models never re-type Office files.
- Search returns small cited snippets instead of whole files; Haiku does the reading.
- Numbers come from SQL (DuckDB), saved as citable calcs — models do no arithmetic.
- A verifier checks every citation, quote and figure; files that fail are not rendered.
- Opus only sees a compact, verified evidence pack, and only in `/rnd:decide`.

Habits that save the most: start each topic with `/rnd:ask` rather than free chat; keep
the chat model on Sonnet (`/model sonnet`) — the `/rnd:*` commands pick their own models
even when the session is on Opus, but free-form questions are answered by the session
model; put new files in `sources/` and they are indexed automatically at the next
session start; cite outputs, never paste documents; check any fact with `/rnd:show <ref>`.
