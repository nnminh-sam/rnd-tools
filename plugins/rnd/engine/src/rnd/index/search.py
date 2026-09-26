"""Retrieval: BM25 over FTS5, optional semantic vectors, fused with Reciprocal Rank Fusion.

The agent (not the engine) does the "AI" part: it rewrites a question into several
keyword queries and passes them all here; fusion rewards chunks that several
phrasings agree on. `exact` mode is grep for documents: substring/regex over blocks.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field

from ..workspace import Workspace
from .store import RefError, Store

RRF_K = 60
_STOP = set(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "have",
        "how",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "was",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "with",
        "does",
        "did",
        "do",
        "can",
        "could",
        "should",
        "would",
        "we",
        "our",
        "you",
        "your",
        "i",
        "me",
        "my",
        "about",
        "into",
        "than",
        "then",
        "there",
    ]
)
_WORD = re.compile(r"[\w][\w'.-]*", re.UNICODE)


@dataclass
class Hit:
    chunk_id: int
    doc_id: str
    anchor: str
    path: str
    doc_type: str
    title: str
    section: str
    snippet: str
    score: float = 0.0
    matched: list[str] = field(default_factory=list)
    best: list[str] = field(default_factory=list)  # anchors of the blocks inside the chunk that match

    @property
    def ref(self) -> str:
        return f"{self.doc_id}#{self.anchor}"


def to_fts_query(q: str, operator: str = "OR") -> str:
    """Natural language -> FTS5 MATCH expression: quoted phrases kept, words OR-ed
    (or AND-ed for the precision pass)."""
    phrases = re.findall(r'"([^"]+)"', q)
    rest = re.sub(r'"[^"]+"', " ", q)
    terms = []
    for w in _WORD.findall(rest):
        w = w.strip(".'-")
        if not w or w.lower() in _STOP:
            continue
        terms.append(w)
    parts = ['"' + p.replace('"', "") + '"' for p in phrases]
    parts += ['"' + t.replace('"', "") + '"' for t in terms]
    return f" {operator} ".join(parts)


def search(
    ws: Workspace,
    queries: list[str],
    k: int = 8,
    doc_types: list[str] | None = None,
    path_glob: str | None = None,
) -> list[Hit]:
    queries = [q for q in (q.strip() for q in queries) if q]
    if not queries:
        return []
    with Store(ws.index_path, readonly=True) as store:
        docs = store.all_docs()
        allowed = [
            d.doc_id
            for d in docs
            if (not doc_types or d.doc_type in doc_types) and (not path_glob or fnmatch.fnmatch(d.path, path_glob))
        ]
        if (doc_types or path_glob) and not allowed:
            return []
        fused: dict[int, Hit] = {}
        scores: dict[int, float] = {}
        pool = max(k * 4, 20)
        passes = []
        for q in queries:
            if to_fts_query(q):
                passes.append((q, to_fts_query(q, "OR")))
                if " OR " in passes[-1][1]:  # precision pass: chunks containing every term
                    passes.append((q, to_fts_query(q, "AND")))
        for q, match in passes:
            rows = store.fts(match, pool, allowed if (doc_types or path_glob) else None)
            for rank, r in enumerate(rows):
                cid = r["id"]
                scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
                if cid not in fused:
                    fused[cid] = Hit(
                        cid,
                        r["doc_id"],
                        r["anchor"],
                        r["path"],
                        r["doc_type"],
                        r["title"] or "",
                        r["section"] or "",
                        r["snip"] or "",
                    )
                if q not in fused[cid].matched:
                    fused[cid].matched.append(q)
        if ws.config.get("semantic"):
            try:
                from . import vectors

                for rank, (cid, _sim) in enumerate(
                    vectors.nearest(ws, store, queries, pool, allowed if (doc_types or path_glob) else None)
                ):
                    scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
                    if cid not in fused:
                        c = store.chunk(cid)
                        if c is None:
                            continue
                        fused[cid] = Hit(
                            cid,
                            c["doc_id"],
                            c["anchor"],
                            c["path"],
                            c["doc_type"],
                            c["title"] or "",
                            c["section"] or "",
                            _lead(c["text"]),
                        )
                    fused[cid].matched.append("~semantic")
            except ImportError:
                pass
        hits = _diversify(sorted(fused.values(), key=lambda h: scores[h.chunk_id], reverse=True), scores, k)
        _pin_blocks(store, hits, queries)
    return hits


def _pin_blocks(store: Store, hits: list[Hit], queries: list[str]) -> None:
    """A chunk spans many blocks (a heading plus a 12-row table); name the blocks inside
    it that match the query, so agents cite `#t1.r10` rather than the whole chunk."""
    stems = {w.lower()[:5] for q in queries for w in _WORD.findall(q) if w.lower() not in _STOP and len(w) > 1}
    for h in hits:
        try:
            _doc, blocks = store.resolve(h.ref)
        except RefError:
            continue
        if len(blocks) <= 1:
            continue
        scored = [(sum(st in b.text.lower() for st in stems), b.anchor) for b in blocks]
        top = max(n for n, _a in scored)
        if top:
            h.best = [a for n, a in scored if n == top][:3]


def _diversify(ordered: list[Hit], scores: dict[int, float], k: int, penalty: float = 0.35) -> list[Hit]:
    """Greedy re-rank that damps repeated hits from one document, so a question whose
    answer spans several sources sees all of them in the top k."""
    picked: list[Hit] = []
    per_doc: dict[str, int] = {}
    pool = list(ordered)
    while pool and len(picked) < k:
        best = max(pool, key=lambda h: scores[h.chunk_id] / (1 + penalty * per_doc.get(h.doc_id, 0)))
        pool.remove(best)
        per_doc[best.doc_id] = per_doc.get(best.doc_id, 0) + 1
        best.score = round(scores[best.chunk_id] * 1000, 2)
        picked.append(best)
    return picked


def _lead(text: str, n: int = 220) -> str:
    t = " ".join(text.split())
    return t[:n] + (" …" if len(t) > n else "")


def format_hits(hits: list[Hit], queries: list[str]) -> str:
    if not hits:
        return (
            f"No results for {queries}. Try synonyms, singular/plural forms, product codes, or exact mode; "
            "run status to confirm the file is indexed."
        )
    lines = [f"{len(hits)} results (read the ref; cite the most specific anchor — the `cite:` blocks when shown):"]
    for i, h in enumerate(hits, 1):
        where = f"{h.doc_type} · {h.path}" + (f" · § {h.section}" if h.section else "")
        lines.append(f"[{i}] {h.ref}  ({where})")
        lines.append("    " + " ".join(h.snippet.split()))
        if h.best:
            lines.append("    cite: " + ", ".join(f"{h.doc_id}#{a}" for a in h.best))
    return "\n".join(lines)


# ------------------------------------------------------------------ exact mode


def exact(
    ws: Workspace,
    pattern: str,
    regex: bool = False,
    k: int = 30,
    doc_types: list[str] | None = None,
    path_glob: str | None = None,
) -> str:
    try:
        rx = re.compile(pattern if regex else re.escape(pattern), re.IGNORECASE)
    except re.error as exc:
        return f"Invalid regex: {exc}"
    out: list[str] = []
    total = 0
    with Store(ws.index_path, readonly=True) as store:
        for d in store.all_docs():
            if doc_types and d.doc_type not in doc_types:
                continue
            if path_glob and not fnmatch.fnmatch(d.path, path_glob):
                continue
            for b in store.blocks(d.doc_id):
                for m in rx.finditer(b.text):
                    total += 1
                    if len(out) < k:
                        s, e = max(0, m.start() - 70), min(len(b.text), m.end() + 70)
                        ctx = " ".join(b.text[s:e].split())
                        out.append(f"{d.doc_id}#{b.anchor}  …{ctx}…")
                    break  # one line per block is enough
    if not out:
        return f"No exact matches for {pattern!r}."
    head = f"{total} block(s) contain {pattern!r}" + (f"; showing {k}" if total > k else "") + ":"
    return "\n".join([head, *out])
