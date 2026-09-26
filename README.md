# RnD — precise, low-cost R&D toolkit for Claude Code

RnD is a Claude Code plugin for research & development teams whose work lives in
**Word, Excel, PowerPoint and PDF** files: reading test reports and interviews, crunching
spreadsheets, writing reports and decks, brainstorming, and making decisions.

It is built for people who already use Claude but tend to run everything on Opus with
long prompts. RnD gives them a small set of commands that:

- **run each step on the cheapest model that can do it precisely** — Haiku finds and
  quotes evidence, Sonnet analyses and writes, Opus only reasons over a compact, verified
  evidence pack (and only in `/rnd:decide`);
- **read documents exactly and cheaply** — a local index returns small, addressable
  snippets (`report#page2`, `deck#s5`, `quotes#Quotes!A14:O14`) instead of whole files;
- **never let a model do arithmetic** — spreadsheet numbers come from SQL (DuckDB) and are
  saved as citable calculations;
- **verify every claim** — a deterministic checker confirms that each citation exists,
  each quote is verbatim and each figure matches its source; Office files are only
  rendered from drafts that pass.

```
you ──/rnd:report──▶ Sonnet orchestrator ─┬─▶ librarian (Haiku)  ─▶ evidence pack ─┐
                                          ├─▶ analyst   (Sonnet) ─▶ SQL calcs ─────┤
                                          └─▶ writer    (Sonnet) ◀─────────────────┘
                                                  │ Markdown with [@citations]
                                                  ▼
                               verifier (no model) ─▶ render ─▶ .docx / .pptx / .pdf / .xlsx
```

## Quick start

Requirements: Claude Code, `git`, and [uv](https://docs.astral.sh/uv/getting-started/installation/).
uv installs the Python engine and its dependencies the first time a session starts
(about 200 MB; seconds on a fast connection, a minute or two on a slow one — Python 3.12
is downloaded too if you don't have it).

### Install from GitHub

In your terminal:

```bash
claude plugin marketplace add nnminh-sam/rnd-tools
```

```bash
claude plugin install rnd@rnd-tools
```

Or inside a Claude Code session: `/plugin marketplace add nnminh-sam/rnd-tools`, then
`/plugin install rnd@rnd-tools`. The full URL works too:
`claude plugin marketplace add https://github.com/nnminh-sam/rnd-tools`.

Restart Claude Code after installing. If the clone fails because your machine has no
GitHub SSH key, set `CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1` and run the add command again.

### Update

New versions are not installed automatically unless you turn on auto-update (`/plugin` →
Marketplaces → `rnd-tools` → Enable auto-update). To update by hand:

```bash
claude plugin marketplace update rnd-tools
```

```bash
claude plugin update rnd@rnd-tools
```

Then restart Claude Code.

### Share with a team

To have everyone who opens a shared project folder offered RnD, run this once in that
folder and commit (or share) the `.claude/settings.json` it writes:

```bash
claude plugin marketplace add nnminh-sam/rnd-tools --scope project
```

### First steps

Open Claude Code in your project folder and run:

```
/rnd:setup
```

Or learn on a realistic furniture R&D project first:

```
/rnd:tutorial
```

Open Claude Code in the folder it creates and follow `TUTORIAL.md` (12 short lessons with
the answers you should get, so you can see the precision for yourself).

> Claude Code ignores a project's `.claude/settings.json` permissions until you have
> opened that folder interactively once and accepted the trust prompt.

## Commands

| Command | What it does | Models |
|---|---|---|
| `/rnd:setup [folder]` | Index a folder; set its default model to Sonnet; pre-approve RnD tools | Haiku |
| `/rnd:ask <question>` | Cited answer from your documents | Haiku |
| `/rnd:analyze <question> [--xlsx]` | Exact numbers via SQL, optional Excel export with chart | Sonnet |
| `/rnd:brainstorm <topic>` | Ideas grounded in evidence, assumptions labelled, shortlist | Haiku → Sonnet |
| `/rnd:report <topic> [--pdf]` | Verified Word/PDF report | Haiku → Sonnet |
| `/rnd:deck <topic>` | Verified PowerPoint with native charts and notes | Haiku → Sonnet |
| `/rnd:decide <question>` | Decision memo: options, trade-offs, confidence, gaps | Haiku → Sonnet → Opus |
| `/rnd:capture <urls or topic>` | Save web sources verbatim so they can be cited | Haiku |
| `/rnd:show <ref>` | The exact source text behind a citation, and where it is in the file | Haiku |
| `/rnd:verify [file] [--deep]` | Check citations/quotes/figures (+ semantic audit) | none (+ Haiku) |
| `/rnd:help [goal]` | Which command to use and why | Haiku |
| `/rnd:tutorial [folder]` | Create the KESTREL demo workspace | Haiku |

Free-form prompts still work: hooks nudge Claude (and you) toward the right command, and
block expensive raw reads of Office/PDF files.

## Why it is cheaper

List prices per million tokens (input/output): Haiku 4.5 $1/$5, Sonnet 5 $2/$10,
Opus 5.5 $4/$20. Routing work away from Opus helps, but reading less helps more. On the
demo workspace the extracted text of all 11 documents is about 27,700 tokens (the survey
spreadsheet alone about 18,500); answering "what are the product targets?" through RnD
search + read returns about 830 tokens with exact anchors — roughly 33× less text to read,
and the survey is queried with SQL instead of being read at all.

Measured end to end from a session set to Opus (headless runs of the tutorial, v0.2.0):

| Lesson | Cost | Models that ran |
|---|---|---|
| `/rnd:ask What are the product targets?` | $0.04 | Haiku only |
| `/rnd:analyze` shell fatigue per material | $0.25 | Sonnet only |
| `/rnd:brainstorm` assembly time | $0.78 | Sonnet + Haiku, no Opus |

## Why it is precise

| Risk | What RnD does |
|---|---|
| Model misreads a document | Deterministic extraction; the model reads exact text by anchor |
| Model invents or rounds numbers | SQL over the source tables; results saved as `[@calc:N]` |
| Quotes are paraphrased | `[@ref "quote"]` is checked character for character |
| Figures drift between draft and source | Every figure in a cited sentence must appear in that source |
| Speculation presented as fact | Uncited figures fail verification; ideas must be labelled |
| Web pages summarised by a model | `capture` stores the page text verbatim with URL and date |
| Broken report goes out | `render` refuses to produce Office files from a failing draft |

## Repository layout

```
.claude-plugin/marketplace.json   marketplace listing (this repo)
plugins/rnd/                      the plugin
  .claude-plugin/plugin.json      manifest
  .mcp.json                       starts the engine's MCP server via uv
  skills/                         /rnd:* commands (+ background "grounding" skill)
  agents/                         librarian, analyst, writer, strategist, ideator, scout, auditor
  hooks/hooks.json                read guard, auto-verify, session briefing, prompt routing
  engine/                         Python package `rnd` (CLI, MCP server, tests)
  demo/                           KESTREL tutorial workspace + TUTORIAL.md (generated)
  evals/                          `claude plugin eval` suite
docs/                             architecture, user guide, developer guide
```

## Documentation

- [User guide](docs/USER-GUIDE.md) — daily workflows, citation syntax, FAQ
- [Architecture](docs/ARCHITECTURE.md) — how the pieces fit, the anchor/citation contract
- [Developing](docs/DEVELOPING.md) — set-up, tests, adding extractors/tools/skills, evals
- [Tutorial](plugins/rnd/demo/TUTORIAL.md) — the KESTREL walkthrough

## License

MIT — see [LICENSE](LICENSE). The KESTREL demo data is entirely fictional.
