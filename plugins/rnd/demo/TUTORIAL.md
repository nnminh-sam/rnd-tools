# RnD tutorial — Project KESTREL

Aldermoor Furniture Co. is developing **KESTREL**, a compact ergonomic task chair for small
home offices. Prototype P2 has been tested: the armrest bracket cracked, assembly takes too
long, and the team must choose a fix for P3 while keeping the landed unit cost at or below
USD 120 and recycled content at or above 50%. Everything here is fictional, but the numbers
are consistent across all documents, so you can check every answer RnD gives you.

The 12 lessons take about 60–90 minutes in total. Each one shows a command to type, what
happens behind the scenes, the answer you should get, and how to check it yourself.

## 0. Before you start

1. **Open Claude Code in this folder** (`cd` into it, then run `claude`) and accept the
   "trust this folder" prompt. Until you do, Claude Code ignores this folder's settings.
2. **Check the model.** This folder's default is Sonnet (`.claude/settings.json`). If you
   pick Opus with `/model`, the `/rnd:*` commands still run their steps on Haiku and
   Sonnet (only `/rnd:decide` uses Opus, for the final reasoning). What Opus changes is
   the cost of your *free-form* questions, which the session model answers.
3. **Keep `/cost` handy**: run it after a lesson to see what the lesson cost.
4. **Where things go:**

| Folder | What is in it |
|---|---|
| `sources/`, `notes/` | the project documents (read-only for RnD) |
| `outputs/` | what RnD writes for you: answers to share, reports, decks, spreadsheets |
| `.rnd/packs/` | evidence packs and `/rnd:ask` answers (Markdown, every fact cited) |
| `.rnd/calcs/` | every SQL result as `N.json` — cited as `[@calc:N]` |

5. **How to read a citation.** Every fact carries one. Show the source behind any of them
   with `/rnd:show <ref>` (Lesson 2).

| Citation | Points to |
|---|---|
| `[@2026-02-09-kickoff-project-kestrel#t1.r3]` | Word document, table 1, row 3 |
| `[@2026-02-09-kickoff-project-kestrel#p14]` | Word document, 14th paragraph |
| `[@tr-2026-031-p2-prototype-test-report#page2]` | PDF, page 2 |
| `[@p2-design-review-2026-08-27#s5.t1]` | PowerPoint, slide 5, its table |
| `[@supplier-quotes-2026-07#Quotes!A8:O8]` | Excel, sheet "Quotes", row 8 |
| `[@calc:5]` | the SQL query and exact result saved in `.rnd/calcs/5.json` |

### The documents

| Doc id | What is inside |
|---|---|
| `2026-02-09-kickoff-project-kestrel` | Word · product targets table (t1), decisions D1–D3, risks |
| `2026-08-20-weekly-sync` | Word · armrest options A/B/C, positions of Finance, Marketing, Engineering, Sourcing |
| `customer-interviews-q2-2026` | Word · 12 interview summaries with quotes, coded pain-point table (t2), synthesis |
| `seating-survey-2026-responses` | Excel · 240 survey responses |
| `competitor-benchmark-2026` | Excel · 8 competitor chairs: price, base size, weight limit, recycled content |
| `seat-shell-materials-test-results` | Excel · shell fatigue (24 samples), materials, seat foam options |
| `tr-2026-031-p2-prototype-test-report` | PDF · the 9 P2 tests, armrest failure analysis, assembly observations |
| `supplier-quotes-2026-07` | Excel · every part with price at 1k/5k/10k units, mass, recycled %, lead time |
| `p2-design-review-2026-08-27` | PowerPoint · P2 vs targets, armrest failure, options and costs, assembly chart |
| `home-office-seating-market-brief-2026` | PDF · market size, price bands, sales channels, reasons for returns |
| `ideas-backlog` | Markdown · the designer's idea backlog |

---

## Lesson 1 — a cited answer (Haiku)

```
/rnd:ask What are the product targets for KESTREL?
```

**Behind the scenes.** The command runs in its own context on the `librarian` agent
(Haiku). It searches with several phrasings, reads the kickoff notes' target table, writes
`.rnd/packs/answer-<slug>.md`, and the verifier checks every citation and figure in it.

**You should get** these 11 targets, each cited to its own table row:

| Target | Value | Citation |
|---|---|---|
| Retail price | USD 349 | `2026-02-09-kickoff-project-kestrel#t1.r2` |
| Unit cost (landed, incl. packaging) | ≤ USD 120 | `2026-02-09-kickoff-project-kestrel#t1.r3` |
| Base diameter | ≤ 600 mm | `2026-02-09-kickoff-project-kestrel#t1.r4` |
| Seat width | 460–490 mm | `2026-02-09-kickoff-project-kestrel#t1.r5` |
| Maximum user weight | 125 kg | `2026-02-09-kickoff-project-kestrel#t1.r6` |
| Recycled content | ≥ 50% by weight | `2026-02-09-kickoff-project-kestrel#t1.r7` |
| Shipping carton | ≤ 0.12 m³, single box | `2026-02-09-kickoff-project-kestrel#t1.r8` |
| Assembly time | ≤ 10 min, included hex key only | `2026-02-09-kickoff-project-kestrel#t1.r9` |
| Seat shell fatigue | ≥ 120,000 cycles | `2026-02-09-kickoff-project-kestrel#t1.r10` |
| Armrest fatigue | ≥ 60,000 cycles | `2026-02-09-kickoff-project-kestrel#t1.r11` |
| Launch | Q2 2027 | `2026-02-09-kickoff-project-kestrel#t1.r12` |

**Check it yourself.** Every bullet should cite a single row (`#t1.r3`), not the whole
table (`#t1`). The answer file in `.rnd/packs/` is plain Markdown; open it in any editor.

## Lesson 2 — check a source

```
/rnd:show 2026-02-09-kickoff-project-kestrel#t1.r3
```

**You should get** the verbatim row — `Target: Unit cost (landed, incl. packaging) | Value:
≤ USD 120 | Rationale: Keeps gross margin above 60% at USD 349 after channel fees.` — plus
where to find it: `sources/meetings/2026-02-09 Kickoff - Project KESTREL.docx` → table 1,
row 3. `/rnd:show calc:N` shows the SQL and the exact rows of a calculation the same way.

## Lesson 3 — counting belongs to SQL

```
/rnd:ask How many interviewees said their chair is too bulky, and what did they say?
```

**You should get** **8 of 12** participants (P01, P03, P05, P06, P07, P09,
P11, P12), counted with SQL over the coded pain-point table in the interview document and
cited as `[@calc:N]`, plus verbatim quotes such as P01's “My chair is wider than the room is
deep…”, P05's “It is a great chair, it is just enormous…” and P07's “Anything with a huge
star base…”. A good answer also says that four of the eight (P03, P06, P09, P11) are coded
"too bulky" but are only quoted about other topics.

**Why it matters.** The count comes from a query, not from the model reading paragraphs;
`/rnd:show calc:N` shows the query.

## Lesson 4 — exact numbers (Sonnet + SQL)

```
/rnd:analyze Mean and minimum cycles to failure per seat shell material; which pass the 120,000-cycle target?
```

**Behind the scenes.** Runs on the `analyst` agent (Sonnet). It lists the SQL tables,
probes the Shell_Fatigue sheet, computes everything in SQL and writes
`outputs/figures-<slug>.md`.

**You should get:**

| Material | Mean cycles | Minimum | Samples ≥ 120,000 | Mean passes |
|---|---|---|---|---|
| PA11-GF bio | 197,466.67 | 188,500 | 6 of 6 | yes |
| PP-GF30 virgin | 176,333.33 | 165,200 | 6 of 6 | yes |
| rPP-50 | 148,250 | 139,800 | 6 of 6 | yes |
| rPP-100 | 107,833.33 | 88,300 | 2 of 6 | **no** |

rPP-100 is the only material below target. The file cites `[@calc:N]` for every figure;
`.rnd/calcs/N.json` holds the SQL and the full-precision result. Four PA11-GF bio samples
stopped at the 200,000-cycle runout, so its real mean is higher — a careful answer says so.

## Lesson 5 — a what-if across documents, exported to Excel

```
/rnd:analyze Landed unit cost and recycled content for the P2 baseline and each armrest option, with and without the EcoLine mechanism --xlsx
```

**You should get** (USD per chair at the 5,000-unit price; recycled % by weight, packaging
excluded):

| Armrest | Mechanism | Unit cost (USD) | Recycled % | Meets both targets |
|---|---|---|---|---|
| P2 baseline | standard | 116.85 | 46.81 | no |
| P2 baseline | EcoLine | 118.15 | 53.45 | **yes** |
| Option A | standard | 117.21 | 46.67 | no |
| Option A | EcoLine | 118.51 | 53.29 | **yes** |
| Option B | standard | 117.95 | 47.93 | no |
| Option B | EcoLine | 119.25 | 54.51 | **yes** |
| Option C | standard | 121.75 | 44.64 | no |
| Option C | EcoLine | 123.05 | 51.23 | no |

Without EcoLine nothing reaches 50% recycled content. With EcoLine, **3
configurations meet both targets**: P2 baseline + EcoLine, Option A + EcoLine, Option B + EcoLine. Option C is over USD 120 either way.
The P2 baseline + EcoLine passes on cost and recycled content, but it keeps the bracket
that cracked — that is why Lesson 9 compares A and B.

**Check it yourself.** Open `outputs/figures-<slug>.xlsx`: typed numbers, a native chart,
and a Provenance sheet with the SQL. The design-review deck rounds the baseline recycled
content to 47%; the exact value is 46.81%.

**Try next:** `/rnd:analyze Option C with EcoLine and the Hanoi seat shell` — USD
122.30, 51.23%: the cheaper shell source still
leaves C over the limit.

## Lesson 6 — grounded brainstorming

```
/rnd:brainstorm How to cut assembly time below 10 minutes
```

**Behind the scenes.** The librarian (Haiku) builds an evidence pack; the `ideator`
(Sonnet) generates 12–20 ideas, links each to its evidence, scores them and writes
`outputs/brainstorm-<slug>.md`. The command stays on Sonnet from start to finish.

**You should get** ideas such as captive screws on the backrest, colour-coded bolts, a
keyed backrest or a QR-code assembly video. Each should cite its motivating evidence: the
P2 mean of 11.6 minutes (range 9.1–14.2), the backrest-to-mechanism step being
the slowest for every tester, P06's “It took me forty…” and P03's “…put the back on the
wrong way, twice.” Assumptions are labelled `Assumption:` and the scoring table is marked
"(judgement)".

## Lesson 7 — a verified Word report

```
/rnd:report P2 test status for the steering committee
```

**Behind the scenes.** Librarians (Haiku) gather 2–4 evidence packs in parallel while
the analyst (Sonnet) computes the figures; the `writer` (Sonnet) drafts
`outputs/<slug>.md`, verifies it and renders the `.docx`. Because the audience is outside
the project team, the `auditor` (Haiku) then checks that every source really says what
the report claims, and the writer fixes whatever it finds. Expect about 10 minutes.

**You should get** a Word file with a summary, the 9 tests (7 passed; T5 armrest fatigue
— cracks at 38,500 and 41,200 cycles against 60,000 — and T9 assembly time — 11.6 min
mean against 10 — failed), status against targets (5 of 8 OK, 2 FAIL, recycled content
MISS), cost and recycled-content status, a numbered Sources list, and the footer
"Citations verified (PASS)".

**See the precision gate work.** Ask Claude: `In the report Markdown, change 38,500 to
39,000`. The verifier reports a `figure-mismatch` immediately and `render` refuses to
produce a new .docx until it is fixed. If you edit the Markdown in your own editor, the
check is not automatic — run `/rnd:verify outputs/<slug>.md`.

## Lesson 8 — check a document before sharing

```
/rnd:verify --deep
```

The deterministic verifier guarantees refs, quotes and figures (no model involved).
`--deep` adds the `auditor` (Haiku), which flags claims the source does not really
support — a count that is off ("six of eight" when the rows show five), a target presented
as a result, "approved" where the source says "evaluate".

## Lesson 9 — the one place Opus is used

```
/rnd:decide Which armrest option should go into P3?
```

**Behind the scenes.** The librarian (Haiku) builds the evidence pack and the analyst
(Sonnet) computes the option figures in parallel; only then does the `strategist` (Opus)
reason over that small pack. The auditor (Haiku) checks the memo and the strategist fixes
what it flags. Expect about 8 minutes.

**A good memo** (`outputs/decision-<slug>.md`):
- rules out **Option C** (flip-up): customers asked for it (5 of 12 raised
  armrests) but it costs USD 121.75 — USD 123.05
  with EcoLine — above the USD 120 limit, with the highest tooling cost (USD 26,000) and the
  longest delay (+8 weeks);
- says **EcoLine is needed** whichever option wins: no configuration reaches 50% recycled
  content without it;
- compares **A + EcoLine** (USD 118.51, 53.29%) and **B + EcoLine** (USD
  119.25, 54.51%): A is cheaper but keeps the zinc casting whose porosity is a
  suspected crack cause (hypothesis H2); B removes both suspected causes, as Engineering
  said in the weekly sync;
- recommends **B + EcoLine with medium confidence**, and lists the gaps: no fatigue data
  for any fix yet, B leaves only USD 0.75 under the cost limit, and the supplier lead
  times and the design review's timeline (+3 / +5 / +8 weeks) are not reconciled.

It should quote kickoff decision D2 exactly — "Evaluate flip-up armrests as an option" —
not as an approval of Option C.

## Lesson 10 — a deck with native charts

```
/rnd:deck P3 armrest decision for the design review
```

**You should get** `outputs/<slug>-deck.pptx`: takeaway titles ("Option B + EcoLine is
the only fix that removes both crack causes within budget", not "Options"), a native
chart built from a calc (click it → "Edit data" in PowerPoint), speaker notes, and Sources
slides. It reuses the evidence from Lesson 9 if you ran it.

## Lesson 11 — evidence from the web

```
/rnd:capture <URL of a public page about office-chair ergonomics>
```

The `scout` (Haiku) saves the page's text verbatim in `sources/web/` with its URL and
fetch date and indexes it. From then on it can be cited like any other document.
Without a URL, `/rnd:capture <topic>` searches the web and captures up to 5 primary
sources.

## Lesson 12 — your own questions

Ask anything about the project. Questions that name the thing you want get the best
answers:

| Vague | Better |
|---|---|
| what is the last two of the seat? | `/rnd:ask What are the last two seat foam options and what do they cost?` |
| is the chair ok? | `/rnd:ask Which P2 tests failed, and by how much?` |
| numbers for the survey | `/rnd:analyze Average willingness to pay by region --xlsx` |

When a question is ambiguous, `/rnd:ask` answers the most likely reading, says which one
it chose (`Assumption: …`) and lists the other readings under Gaps, so you can re-ask.

---

## What to expect in time and cost

| Lesson | Models | Typical time |
|---|---|---|
| 1–3 `/rnd:ask`, `/rnd:show` | Haiku | under 1–2 min |
| 4–5 `/rnd:analyze` | Sonnet | 2–4 min |
| 6 `/rnd:brainstorm` | Haiku → Sonnet | about 5 min |
| 7 `/rnd:report` (with audit) | Haiku → Sonnet → Haiku | about 10 min |
| 9 `/rnd:decide` (with audit) | Haiku + Sonnet → Opus → Haiku | about 8 min |

List prices per million tokens (input/output): Haiku $1/$5, Sonnet $2/$10, Opus $4/$20.
Run `/cost` after a lesson for the real figure.

## If something looks wrong

| You see | What it means / what to do |
|---|---|
| A figure different from this tutorial | A bug — please report it with the answer file from `.rnd/packs/` or `outputs/`. |
| `FAIL … figure-mismatch` | A number is not in the cited source at the precision written. Claude fixes it; if you edited by hand, fix the number or cite the right row. |
| `uncited-figure` | A sentence states a number without a citation. |
| `bad-quote` | A quoted phrase is not word-for-word in the source. |
| `WARN … broad-ref` | The citation points at a whole table or long range; cite the row. |
| "Read was denied for a .pdf/.docx" | On purpose: RnD reads the exact part instead of the whole file. |
| An agent "stalled" | Usually the computer slept. Ask Claude to run that step again. |
| The RnD tools are missing | Run `/rnd:setup`; if it still fails, `/mcp` → reconnect `plugin:rnd:rnd`. |

## What to take away

- Start with a `/rnd:*` command instead of free chat: each one picks the cheapest model
  that can do the job, and checks the result.
- Never paste or open whole documents; RnD reads the part that matters, exactly.
- Every number traces to a document row or a calc — check any of them with `/rnd:show`.
- For your own project: make a folder, put documents in `sources/`, open Claude Code
  there and run `/rnd:setup`. See the user guide for more.
