---
name: tutorial
description: Create the KESTREL demo workspace (a realistic furniture R&D project — a compact ergonomic chair with interviews, survey data, material tests, a prototype test report, supplier quotes and a design-review deck) and guide the user through the RnD commands on it.
argument-hint: "[target folder]"
model: haiku
allowed-tools: mcp__plugin_rnd_rnd__setup
---

Create and introduce the RnD tutorial workspace.

1. Target folder: `$ARGUMENTS` if given, otherwise `~/RnD-tutorial/kestrel-chair`.
2. Call the RnD `setup` tool with `path` = that folder and `demo: true` (it copies the
   demo project, configures it and indexes it).
3. Tell the user, briefly:
   - The scenario: Aldermoor Furniture is developing KESTREL, a compact ergonomic task
     chair. Prototype P2 was just tested: an armrest bracket cracked, assembly is too
     slow, and the team must choose a fix while keeping unit cost ≤ USD 120 and recycled
     content ≥ 50%. All data is fictional but internally consistent, so every answer
     can be checked.
   - To continue: open a new Claude Code session **in that folder** (so its settings
     and CLAUDE.md apply) and follow `TUTORIAL.md`, or try the lessons below.
4. Show the lesson list (one line each), and say that `TUTORIAL.md` has, for every
   lesson, what happens behind the scenes, the exact answer to expect and how to check it:
   1. `/rnd:ask What are the product targets for KESTREL?`
   2. `/rnd:show 2026-02-09-kickoff-project-kestrel#t1.r3`
   3. `/rnd:ask How many interviewees said their chair is too bulky, and what did they say?`
   4. `/rnd:analyze Mean and minimum cycles to failure per seat shell material; which pass the 120,000-cycle target?`
   5. `/rnd:analyze Landed unit cost and recycled content for the P2 baseline and each armrest option, with and without the EcoLine mechanism --xlsx`
   6. `/rnd:brainstorm How to cut assembly time below 10 minutes`
   7. `/rnd:report P2 test status for the steering committee`
   8. `/rnd:verify --deep`
   9. `/rnd:decide Which armrest option should go into P3?`
   10. `/rnd:deck P3 armrest decision for the design review`
   11. `/rnd:capture <a public web page about office-chair ergonomics>`
   12. Your own questions — `TUTORIAL.md` shows how to phrase them.
