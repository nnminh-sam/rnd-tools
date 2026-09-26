"""Deterministic citation verifier — the precision gate for everything RnD writes.

For a Markdown file it checks that:
  1. every [@ref] resolves to an indexed location or a saved calc        (error)
  2. every quoted string appears verbatim in the cited evidence          (error)
  3. every figure in a cited sentence appears in its cited evidence,
     at the precision it is written (148,233 / 148k / 45% vs 0.45);
     dates count as one figure (9 February 2026 = 2026-02-09) and
     spelled-out counts are figures too ("six of eight")                (error)
  4. no sentence states a figure without any citation                    (error)
  5. overall prose citation coverage; refs too broad to check by eye     (warning)

A table row without its own citation uses the citation of the table's header row or
of the heading/caption line directly above the table ("Results [@calc:8]:").

Units tagged as assumptions / hypotheses / ideas / recommendations are exempt from
3–4 and counted separately, so speculation is allowed but always visibly labelled.
A sentence tagged "(derived)" states a figure worked out by hand; it is not
number-checked but is listed so a reviewer can re-check it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .cite import CITE_GROUP, Citation, find_citations, strip_citations
from .index.store import RefError, Store
from .util import evidence_numbers, find_count_words, find_dates, find_numbers, numbers_match
from .workspace import Workspace

EXEMPT_PREFIX = re.compile(
    r"^\s*(?:[-*+]\s+|\d+[.)]\s+)?(?:\*\*|__)?\s*(?:💡\s*)?"
    r"(assumption|hypothesis|idea|recommendation|recommend|opinion|question|open question|next step|proposal|"
    r"option [a-z0-9]+|risk|giả định|giả thuyết|ý tưởng|đề xuất|khuyến nghị)s?\b",
    re.IGNORECASE,
)
EXEMPT_TAG = re.compile(
    r"\((assumption|hypothesis|estimate|idea|judgement|judgment|giả định|giả thuyết|đánh giá)\)", re.IGNORECASE
)
DERIVED_TAG = re.compile(r"\((derived|tính toán)\)", re.IGNORECASE)
SKIP_SECTION = re.compile(
    r"^(sources|references|bibliography|(evidence )?gaps?|open questions|searched|nguồn|tài liệu tham khảo)\b",
    re.IGNORECASE,
)
# numbers that label things rather than state facts: "Table 2", "Step 3", "Top 5", "P2"
LABEL_BEFORE = re.compile(
    r"(figure|fig\.|table|section|step|phase|top|slide|page|chapter|appendix|item|no\.|#|option|round|week|"
    r"sprint|version|tier|level|calc\s*:|bảng|hình|mục|bước)\s*$",
    re.IGNORECASE,
)
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[\"“(\[A-Z0-9À-Ỹ*_])")


@dataclass
class Issue:
    level: str  # error | warn | info
    line: int
    code: str
    message: str


@dataclass
class Report:
    path: str
    citations: int = 0
    citations_ok: int = 0
    units: int = 0
    units_cited: int = 0
    units_exempt: int = 0
    figures_checked: int = 0
    figures_ok: int = 0
    issues: list[Issue] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def status(self) -> str:
        if self.errors:
            return "FAIL"
        return "WARN" if any(i.level == "warn" for i in self.issues) else "PASS"

    def to_text(self, max_issues: int = 40) -> str:
        cov = f"{self.units_cited}/{self.units - self.units_exempt}" if self.units else "0/0"
        lines = [
            f"{self.status}: {self.path}",
            f"citations {self.citations_ok}/{self.citations} resolved · figures {self.figures_ok}/{self.figures_checked} "
            f"backed by evidence · statements cited {cov} (+{self.units_exempt} labelled assumptions/ideas)",
        ]
        shown = sorted(self.issues, key=lambda i: ({"error": 0, "warn": 1, "info": 2}[i.level], i.line))
        for i in shown[:max_issues]:
            lines.append(f"  {i.level.upper():5} L{i.line} [{i.code}] {i.message}")
        if len(shown) > max_issues:
            lines.append(f"  … {len(shown) - max_issues} more")
        if self.status == "FAIL":
            lines.append(
                "Fix: correct the ref/anchor (search or outline), quote verbatim, take figures from the cited text "
                "or cite a [@calc:n] from the sql tool, or label speculation as 'Assumption:'/'Hypothesis:'."
            )
        return "\n".join(lines)

    def evidence_text(self, max_chars: int = 700) -> str:
        """Claims paired with their evidence, for a semantic (LLM) audit."""
        out = []
        for n, e in enumerate(self.evidence, 1):
            out.append(f"### Claim {n} (L{e['line']})\n{e['claim']}")
            for ref, ev in e["sources"]:
                ev = " ".join(ev.split())
                out.append(f"- [{ref}] {ev[:max_chars]}{' …' if len(ev) > max_chars else ''}")
        return "\n".join(out) if out else "(no cited claims)"


def _norm(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-").replace(" ", " ")
    return " ".join(s.split()).lower()


def quote_found(quote: str, evidence: str) -> bool:
    ev = _norm(evidence)
    pos = 0
    for part in re.split(r"\s*(?:\.\.\.|…|\[\.\.\.\])\s*", quote):
        part = _norm(part).strip(" .,;:")
        if not part:
            continue
        idx = ev.find(part, pos)
        if idx < 0:
            return False
        pos = idx + len(part)
    return True


def _claim_figures(sentence: str):
    clean = strip_citations(sentence)
    clean = re.sub(r"`[^`]*`", "", clean)
    clean = re.sub(r"\]\([^)]*\)", "]", clean)  # link targets
    clean = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", clean)  # list markers
    dates = find_dates(clean)
    for d in dates:  # a date is one figure, not three numbers
        clean = clean[: d.start] + " " * (d.end - d.start) + clean[d.end :]
    out = list(dates)
    for n in find_numbers(clean):
        if LABEL_BEFORE.search(clean[: n.start]):
            continue
        out.append(n)
    return out + find_count_words(clean)


@dataclass
class _Unit:
    line: int
    text: str
    exempt: bool = False  # e.g. a row of a table whose header is tagged "(judgement)"


def _units(markdown: str) -> list[_Unit]:
    """Split Markdown into checkable statements (paragraphs, list items, table rows)."""
    lines = markdown.split("\n")
    units: list[_Unit] = []
    i = 0
    if lines and lines[0].strip() == "---":  # frontmatter
        for j in range(1, len(lines)):
            if lines[j].strip() == "---":
                i = j + 1
                break
    in_code = False
    skip_level = 0
    para: list[str] = []
    para_line = 0
    in_comment = False
    table_exempt = False
    table_cites = ""

    def flush() -> None:
        nonlocal para
        if para:
            units.append(_Unit(para_line, " ".join(s.strip() for s in para)))
            para = []

    while i < len(lines):
        raw = lines[i]
        s = raw.strip()
        ln = i + 1
        i += 1
        if in_comment:
            if "-->" in s:
                in_comment = False
            continue
        if s.startswith("<!--"):
            flush()
            in_comment = "-->" not in s
            continue
        if s.startswith("```") or s.startswith("~~~"):
            flush()
            in_code = not in_code
            continue
        if in_code:
            continue
        h = re.match(r"^(#{1,6})\s+(.*)$", s)
        if h:
            flush()
            level = len(h.group(1))
            if skip_level and level <= skip_level:
                skip_level = 0
            if not skip_level and SKIP_SECTION.match(h.group(2).strip()):
                skip_level = level
            continue
        if skip_level:
            continue
        if not s or s in ("---", "***", "___"):
            flush()
            continue
        if s.startswith("|"):
            flush()
            if re.match(r"^\|?\s*:?-{2,}", s):
                continue
            # header row = row followed by a separator
            nxt = lines[i].strip() if i < len(lines) else ""
            if re.match(r"^\|?\s*:?-{2,}", nxt):
                table_exempt = bool(EXEMPT_TAG.search(s))
                table_cites = " ".join(m.group(0) for m in CITE_GROUP.finditer(s)) or _caption_cites(lines, ln - 2)
                continue
            # a row without its own citation is checked against the table's caption/header citation
            units.append(_Unit(ln, s if "[@" in s or not table_cites else f"{s} {table_cites}", table_exempt))
            continue
        table_exempt = False
        table_cites = ""
        if re.match(r"^([-*+]|\d+[.)])\s+", s) or s.startswith(">"):
            flush()
            para = [s.lstrip("> ")]
            para_line = ln
            continue
        if not para:
            para_line = ln
        para.append(s)
    flush()
    return units


_CAPTION = re.compile(r"^(#{1,6}\s|table\b|source|data\b|figures?\b|bảng|nguồn)", re.IGNORECASE)


def _caption_cites(lines: list[str], idx: int) -> str:
    """Citations of the heading or caption line right above a table ('Results [@calc:8]:')."""
    while idx >= 0 and not lines[idx].strip():
        idx -= 1
    if idx < 0:
        return ""
    line = lines[idx].strip()
    bare = strip_citations(line).strip()
    if not (_CAPTION.match(line) or bare.endswith(":")):
        return ""
    return " ".join(m.group(0) for m in CITE_GROUP.finditer(line))


_CITE_AFTER_STOP = re.compile(r"([.!?])((?:\s*\[@[^\]\n]+\])+)")


def _sentences(unit_text: str) -> list[str]:
    if unit_text.startswith("|"):
        return [unit_text]
    # "claim. [@ref]" -> "claim [@ref]." so the citation stays with its sentence
    text = _CITE_AFTER_STOP.sub(lambda m: " " + m.group(2).strip() + m.group(1), unit_text)
    return [p for p in _SENT_SPLIT.split(text) if p.strip()]


def _sentence_citations(sentences: list[str]) -> list[list[Citation]]:
    """Own citations per sentence; an uncited sentence borrows from the next cited
    sentence in the same paragraph ("A. B [@x]."), else from the previous one."""
    own = [[c for _m, cs, _b in find_citations(s) for c in cs] for s in sentences]
    out: list[list[Citation]] = []
    for i, cites in enumerate(own):
        if cites:
            out.append(cites)
            continue
        nxt = next((own[j] for j in range(i + 1, len(own)) if own[j]), None)
        prev = next((own[j] for j in range(i - 1, -1, -1) if own[j]), None)
        out.append(nxt or prev or [])
    return out


_SQL_NUMBER = re.compile(r"(?<![\w.'])(\d+(?:\.\d+)?)(?![\w.'])")
NO_INDEX = "workspace index missing (.rnd/index.sqlite) — run /rnd:setup or the index tool"
BROAD_REF_BLOCKS = 10  # a ref spanning more blocks than this is hard for a reader to check


class _Evidence:
    def __init__(self, ws: Workspace, store: Store | None):
        self.ws = ws
        self.store = store
        self.cache: dict[str, tuple[str | None, list[float], str | None]] = {}
        self.n_blocks: dict[str, int] = {}

    def get(self, c: Citation) -> tuple[str | None, list[float], str | None]:
        """Returns (evidence_text, numbers, error)."""
        if c.ref in self.cache:
            return self.cache[c.ref]
        if c.is_calc:
            path = self.ws.calcs_dir / f"{c.calc_id}.json"
            if not path.exists():
                res = (None, [], f"{c.ref} not found (calcs are created by the sql tool)")
            else:
                calc = json.loads(path.read_text())
                nums: list[float] = []
                texts = [" ".join(calc.get("columns", []))]
                for row in calc.get("rows", []):
                    for v in row:
                        if isinstance(v, bool):
                            continue
                        if isinstance(v, (int, float)):
                            nums.append(float(v))
                        elif v is not None:
                            texts.append(str(v))
                            nums += evidence_numbers(str(v))
                sql = calc.get("sql", "")
                nums += [float(x) for x in _SQL_NUMBER.findall(sql)]  # thresholds stated in the query
                res = (sql + "\n" + " | ".join(texts), nums, None)
        elif self.store is None:
            res = (None, [], NO_INDEX)
        else:
            try:
                doc, blocks = self.store.resolve(c.ref)
                text = "\n".join(b.text for b in blocks)
                # the document's own date (in its title or file name) is part of every citation of it
                doc_dates = [d.value for d in find_dates(f"{doc.title} {Path(doc.path).stem}")]
                res = (text, evidence_numbers(text) + doc_dates, None)
                self.n_blocks[c.ref] = len(blocks)
            except RefError as exc:
                res = (None, [], str(exc))
        self.cache[c.ref] = res
        return res


def verify_markdown(ws: Workspace, markdown: str, label: str = "<text>", collect_evidence: bool = False) -> Report:
    rep = Report(label)
    store = Store(ws.index_path, readonly=True) if ws.index_path.exists() else None
    ev = _Evidence(ws, store)
    no_index_reported = False
    broad_reported: set[str] = set()
    try:
        prose_units = 0
        for unit in _units(markdown):
            groups = find_citations(unit.text)
            unit_cites: list[Citation] = []
            for _m, cites, bad in groups:
                for b in bad:
                    rep.issues.append(Issue("error", unit.line, "malformed", f"cannot parse citation '[@{b}]'"))
                unit_cites += cites
            exempt = unit.exempt or bool(EXEMPT_PREFIX.match(unit.text) or EXEMPT_TAG.search(unit.text))
            has_text = len(strip_citations(unit.text).strip()) > 25
            rep.units += 1
            if exempt:
                rep.units_exempt += 1
            elif unit_cites:
                rep.units_cited += 1
            if has_text and not exempt:
                prose_units += 1

            # 1 + 2: refs and quotes
            reported: set[str] = set()
            for c in unit_cites:
                rep.citations += 1
                text, _nums, err = ev.get(c)
                if err == NO_INDEX:
                    if not no_index_reported:  # one error per file, not one per citation
                        rep.issues.append(Issue("error", unit.line, "no-index", err))
                        no_index_reported = True
                    continue
                if err:
                    if c.ref not in reported:  # one error per dead ref per statement
                        rep.issues.append(Issue("error", unit.line, "unknown-ref", err))
                        reported.add(c.ref)
                    continue
                if ev.n_blocks.get(c.ref, 0) > BROAD_REF_BLOCKS and c.ref not in broad_reported:
                    broad_reported.add(c.ref)
                    rep.issues.append(
                        Issue(
                            "warn",
                            unit.line,
                            "broad-ref",
                            f"{c.ref} spans {ev.n_blocks[c.ref]} blocks — cite the exact row/paragraph/page "
                            "that holds the fact so a reader can find it",
                        )
                    )
                if c.quote is not None and not quote_found(c.quote, text or ""):
                    rep.issues.append(
                        Issue("error", unit.line, "bad-quote", f'quote not found verbatim in {c.ref}: "{c.quote[:80]}"')
                    )
                    continue
                rep.citations_ok += 1

            # 3 + 4: figures
            sentences = _sentences(unit.text)
            for sent, sent_cites in zip(sentences, _sentence_citations(sentences)):
                figures = _claim_figures(sent)
                if collect_evidence and sent_cites and strip_citations(sent).strip():
                    rep.evidence.append(
                        {
                            "line": unit.line,
                            "claim": re.sub(r"\s+([.,;:!?])", r"\1", strip_citations(sent)).strip(),
                            "sources": [(c.ref, ev.get(c)[0] or "(unresolved)") for c in sent_cites],
                        }
                    )
                if not figures or exempt:
                    continue
                if DERIVED_TAG.search(sent):
                    rep.issues.append(
                        Issue(
                            "info",
                            unit.line,
                            "derived",
                            f"hand-derived figure(s) {', '.join(f.text for f in figures)} — re-check or compute via sql",
                        )
                    )
                    continue
                if not sent_cites:
                    rep.issues.append(
                        Issue(
                            "error",
                            unit.line,
                            "uncited-figure",
                            f"figure(s) {', '.join(f.text for f in figures)} with no citation: "
                            f'"{strip_citations(sent).strip()[:90]}"',
                        )
                    )
                    continue
                live = [c for c in sent_cites if ev.get(c)[2] is None]
                if not live:  # already reported as unknown-ref; a figure check would only add noise
                    continue
                pool: list[float] = []
                for c in live:
                    pool += ev.get(c)[1]
                for f in figures:
                    rep.figures_checked += 1
                    if numbers_match(f, pool):
                        rep.figures_ok += 1
                    else:
                        refs = ", ".join(dict.fromkeys(c.ref for c in live))
                        rep.issues.append(
                            Issue(
                                "error",
                                unit.line,
                                "figure-mismatch",
                                f"'{f.text}' not found in cited evidence ({refs})",
                            )
                        )
        if prose_units >= 5 and rep.units_cited < 0.5 * max(1, prose_units - rep.units_exempt):
            rep.issues.append(
                Issue("warn", 0, "low-coverage", f"only {rep.units_cited} of {prose_units} statements carry a citation")
            )
    finally:
        if store:
            store.close()
    return rep


def verify_file(ws: Workspace, path: Path | str, collect_evidence: bool = False) -> Report:
    p = ws.abspath(path).resolve()
    if not p.is_relative_to(ws.root.resolve()):
        raise ValueError(
            f"{p} is outside the workspace {ws.root}. Write drafts to {ws.root / 'outputs'}/ and packs to "
            f"{ws.packs_dir}/ (absolute paths), then verify that file."
        )
    return verify_markdown(ws, p.read_text(encoding="utf-8"), ws.rel(p), collect_evidence)
