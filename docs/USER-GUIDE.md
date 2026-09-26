# RnD user guide

For R&D engineers, product managers and researchers who use Claude Code to work with
project documents. You do not need to know about agents, skills or hooks — RnD handles
those. You only need the commands below and three habits.

## The three habits

1. **Start with a command, not a chat.** `/rnd:ask`, `/rnd:analyze`, `/rnd:report`… each
   one picks the cheapest model that can do the job and checks the result. Free-form
   prompts work too, but cost more and are not always verified.
2. **Keep documents in the workspace, not in the chat.** Don't paste or attach files.
   Put them in `sources/` (any sub-folder); they are indexed automatically when a session
   starts, or run `/rnd:setup` again.
3. **Trust citations, not prose.** Every fact carries `[@doc#anchor]` or `[@calc:N]`. If a
   sentence has a number and no citation, it has not been checked.

## Setting up a project

1. Create a folder for the project (one workspace per product or research topic works
   well) with sub-folders such as `sources/market`, `sources/tests`, `notes`.
2. Open Claude Code in that folder, accept the trust prompt, run `/rnd:setup`.
3. Restart Claude Code once so the folder's default model (Sonnet) applies.

`/rnd:setup` creates:

| Path | Purpose |
|---|---|
| `.rnd/` | index, data tables, saved calculations, evidence packs (safe to delete: rebuilt by setup) |
| `outputs/` | everything RnD writes for you: figures (`figures-*.md/.xlsx`), reports, decks, memos |
| `.claude/settings.json` | default model Sonnet; RnD tools pre-approved |
| `CLAUDE.md` | short grounding rules loaded into every session |

Supported files: `.docx .xlsx .xlsm .pptx .pdf .md .txt .csv .html`. Legacy `.doc/.xls/.ppt`
must be re-saved in the modern format. Scanned PDFs without a text layer are listed as
warnings (run OCR in Acrobat or similar first).

## Which command?

| Goal | Command | Example |
|---|---|---|
| A fact, quote, summary of what documents say | `/rnd:ask` | `/rnd:ask What did the P2 test report conclude about the armrest?` |
| Numbers | `/rnd:analyze` | `/rnd:analyze Average willingness to pay by region --xlsx` |
| Options for a problem | `/rnd:brainstorm` | `/rnd:brainstorm Ways to reduce shipping carton volume` |
| A document for others | `/rnd:report` | `/rnd:report Material selection summary --pdf` |
| Slides | `/rnd:deck` | `/rnd:deck Steering committee update --slides 8` |
| A decision | `/rnd:decide` | `/rnd:decide Should we switch the base to nylon?` |
| Outside evidence | `/rnd:capture` | `/rnd:capture https://example.org/standard-overview` |
| See the source of a citation | `/rnd:show` | `/rnd:show 2026-02-09-kickoff-project-kestrel#t1.r3` |
| Check a document | `/rnd:verify` | `/rnd:verify outputs/material-summary.md --deep` |

Not sure? `/rnd:help <what you want to do>`.

## Reading citations

| Citation | Where to look |
|---|---|
| `[@kickoff-notes#p12]` | 12th paragraph (non-empty) of the kickoff notes |
| `[@kickoff-notes#t1.r3]` | table 1, row 3 |
| `[@test-report#page2]` | page 2 of the PDF |
| `[@design-review#s5.t1]` | slide 5, its table |
| `[@quotes#Quotes!A14:O14]` | sheet "Quotes", row 14 |
| `[@calc:7]` | `.rnd/calcs/7.json` — the SQL query and its exact result |

To see what a citation points to, run `/rnd:show <ref>` (several refs at once are fine):
it prints the exact text, the file and the location in words ("table 1, row 3"), or for a
calc the SQL and its rows.

In Word/PDF/PowerPoint outputs citations become `[1]`, `[2]`… with a Sources list that
names the file and the location in plain words (page, slide, sheet and cells).

## Editing drafts yourself

Drafts are Markdown in `outputs/`. You can edit them in any editor or ask Claude to. When
Claude saves a draft, it is verified automatically; when *you* save one in your editor,
nothing runs — check it with `/rnd:verify outputs/<file>.md`. To render after editing by
hand:

```
Render outputs/p2-status.md to docx
```

Rules the checker applies:

- Figures must match the cited source at the precision you write. "about 150,000" may
  round 148,250; a bare "150,000" may not.
- Quotes in `"…"` inside a citation must be exact.
- Opinions and speculation are welcome when labelled: start the sentence with
  `Assumption:`, `Hypothesis:`, `Idea:`, `Recommendation:` or `Risk:`; put `(judgement)`
  in a header cell of a scoring table.
- Counts written in words are checked too: "six of eight targets pass" must match the
  cited source or calc.
- In a table, cite each row, add a Source column, or put the citation on a caption line
  right above the table (`Cost per option [@calc:5]:`) — every row is then checked
  against it.
- A figure you worked out by hand can be tagged `(derived)`; it is listed for review
  instead of failing — but prefer asking `/rnd:analyze` to compute it.
- `broad-ref` (warning): the citation points at a whole table or a long range; cite the
  row or paragraph so readers can find the fact.

## Templates

- Word: `render … template: corporate.docx` uses that document's styles (Title, Heading 1–4,
  List Bullet, Quote, table styles).
- PowerPoint: `/rnd:deck … --template brand.pptx` uses the template's layouts 0 (title),
  1 (title + content) and 5 (title only).

## Editing existing Office files

Ask in plain words, e.g. "In the supplier quotes workbook set Quotes!K3 to 5.10" or
"In the weekly sync notes replace 'No decision taken.' with 'Decision: option B.'".
RnD writes `<name>.edited.<ext>` next to the original unless you ask for an in-place edit
(then a backup goes to `.rnd/backups/`). Workbooks with charts or images are never
rewritten in place, because the Excel library cannot preserve them.

## Keeping costs down

- Use `/model sonnet` for everyday chat in research folders (setup makes it the default).
  At list prices Sonnet costs half as much as Opus per token, Haiku a quarter. The
  `/rnd:*` commands pick their own models even when you choose Opus; your free-form
  questions are what Opus makes expensive.
- Ask narrow questions; `/rnd:ask` twice is cheaper than one sprawling Opus conversation.
- Reuse evidence packs: they are saved in `.rnd/packs/`; mention one ("use the pack from
  the armrest decision") and agents read it instead of searching again.
- Run `/cost` after a task to see what it cost.

## FAQ

**"Read was denied for a .pdf/.docx file."** On purpose: reading an Office/PDF file
directly loads all of it into context and loses its structure. Claude is told which RnD
tool to use instead; nothing is needed from you.

**"Refusing to render: citation verification failed."** The draft has an unsupported
figure, a wrong quote or a broken ref. Ask Claude to fix the listed issues, or
`/rnd:verify` to see them.

**A figure I know is correct fails.** The cited location may not contain it — cite the row
or page that does, or compute it with `/rnd:analyze` and cite the calc.

**A new file is not found.** It is indexed at the next session start; to index now, ask
"re-index the workspace" or run `/rnd:setup`.

**Semantic search?** Exact-term search plus the librarian's synonym expansion covers most
needs. For large multilingual corpora, set `"semantic": true` in `.rnd/config.json` and
install the extra (`uv sync --extra semantic` in the plugin's `engine/` folder).

**The RnD tools are missing.** Run `/rnd:setup`; it checks for `uv` and installs the
engine. Then `/mcp` → reconnect `plugin:rnd:rnd`.
