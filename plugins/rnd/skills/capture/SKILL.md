---
name: capture
description: Bring web evidence into the workspace verbatim — capture given URLs, or research a topic online and capture the best primary sources (standards, statistics, manufacturer data, papers) so they can be quoted and cited. Runs on Haiku.
argument-hint: "<url ...> | <topic to research>"
context: fork
agent: rnd:scout
model: haiku
background: false
---

Bring web evidence into the RnD workspace for: **$ARGUMENTS**

- If the arguments contain URLs, `capture` exactly those (no search).
- Otherwise research the topic following your method and capture at most 5 primary
  sources.
- Return the table of captured documents (doc id, title, URL, why relevant, one cited
  key fact) and one line per rejected or failed page.
