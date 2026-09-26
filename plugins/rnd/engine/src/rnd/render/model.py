"""Markdown -> a small document model shared by the docx, pdf and pptx renderers.

Models write Markdown (cheap, diffable, verifiable); renderers turn it into Office
files deterministically. Supported Markdown:

    frontmatter (title, subtitle, author, date)   # / ## / ### headings
    paragraphs with **bold**, *italic*, `code`, links, [@citations]
    bullet / numbered lists (nested)   pipe tables   > quotes   --- (slide break in pptx)
    <!-- notes: speaker notes -->      ![caption](path/to/image.png)
    ```chart                            charts from a saved calc or inline CSV
    type: bar | column | line | pie
    title: Mean cycles by material
    calc: 3            # or:  data: + CSV lines below
    x: material
    y: mean_cycles
    ```
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from typing import Any

from ..cite import CITE_GROUP, Citation, parse_group
from ..util import human_location


@dataclass
class Run:
    text: str
    bold: bool = False
    italic: bool = False
    code: bool = False
    link: str | None = None
    cites: list[int] | None = None  # citation numbers; text is empty for a citation run


@dataclass
class Block:
    kind: str  # heading | para | list | table | quote | code | chart | rule | notes | image
    runs: list[Run] = field(default_factory=list)
    level: int = 0
    ordered: bool = False
    items: list[tuple[int, list[Run]]] = field(default_factory=list)  # lists: (depth, runs)
    header: list[list[Run]] = field(default_factory=list)
    rows: list[list[list[Run]]] = field(default_factory=list)
    text: str = ""  # code / notes / image path
    spec: dict[str, Any] = field(default_factory=dict)  # chart


@dataclass
class Source:
    number: int
    ref: str
    quote: str | None = None


@dataclass
class DocModel:
    meta: dict[str, str]
    blocks: list[Block]
    sources: list[Source]

    @property
    def title(self) -> str:
        return self.meta.get("title") or next((runs_text(b.runs) for b in self.blocks if b.kind == "heading"), "Report")


def runs_text(runs: list[Run]) -> str:
    return "".join(r.text for r in runs)


class _Citations:
    def __init__(self) -> None:
        self.by_ref: dict[str, int] = {}
        self.sources: list[Source] = []

    def number(self, c: Citation) -> int:
        if c.ref not in self.by_ref:
            self.by_ref[c.ref] = len(self.sources) + 1
            self.sources.append(Source(self.by_ref[c.ref], c.ref, c.quote))
        return self.by_ref[c.ref]


def _split_citations(text: str, base: Run, cites: _Citations) -> list[Run]:
    out: list[Run] = []
    pos = 0
    for m in CITE_GROUP.finditer(text):
        chunk = text[pos : m.start()].rstrip(" ")  # "claim [@x]." -> "claim¹."
        if chunk:
            out.append(Run(chunk, base.bold, base.italic, base.code, base.link))
        parsed, _bad = parse_group(m.group("body"))
        if parsed:
            out.append(Run("", cites=[cites.number(c) for c in parsed]))
        pos = m.end()
    if pos < len(text):
        out.append(Run(text[pos:], base.bold, base.italic, base.code, base.link))
    return out


def _inline(token, cites: _Citations) -> list[Run]:
    runs: list[Run] = []
    bold = italic = False
    link: str | None = None
    for child in token.children or []:
        t = child.type
        if t == "strong_open":
            bold = True
        elif t == "strong_close":
            bold = False
        elif t == "em_open":
            italic = True
        elif t == "em_close":
            italic = False
        elif t == "link_open":
            link = child.attrs.get("href")
        elif t == "link_close":
            link = None
        elif t == "code_inline":
            runs.append(Run(child.content, bold, italic, True, link))
        elif t in ("softbreak", "hardbreak"):
            runs.append(Run(" " if t == "softbreak" else "\n", bold, italic))
        elif t == "text":
            runs += _split_citations(child.content, Run("", bold, italic, False, link), cites)
        elif t == "image":
            runs.append(Run(child.content or child.attrs.get("alt", ""), bold, italic))
        elif t == "html_inline":
            continue
    return [r for r in runs if r.text or r.cites]


def _frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    lines = text.split("\n")
    for i in range(1, min(len(lines), 60)):
        if lines[i].strip() == "---":
            meta = {}
            for ln in lines[1:i]:
                if ":" in ln:
                    k, v = ln.split(":", 1)
                    meta[k.strip().lower()] = v.strip().strip('"')
            return meta, "\n".join(lines[i + 1 :])
    return {}, text


def parse_chart(body: str) -> dict[str, Any]:
    spec: dict[str, Any] = {}
    lines = body.strip("\n").split("\n")
    for i, ln in enumerate(lines):
        if ln.strip().lower() == "data:":
            spec["data"] = list(csv.reader(io.StringIO("\n".join(lines[i + 1 :]))))
            break
        if ":" in ln:
            k, v = ln.split(":", 1)
            spec[k.strip().lower()] = v.strip()
    return spec


def parse(markdown: str) -> DocModel:
    from markdown_it import MarkdownIt

    meta, body = _frontmatter(markdown)
    md = MarkdownIt("commonmark", {"html": True}).enable("table")
    tokens = md.parse(body)
    cites = _Citations()
    blocks: list[Block] = []
    i = 0
    list_stack: list[bool] = []
    cur_list: Block | None = None
    quote_depth = 0
    while i < len(tokens):
        tok = tokens[i]
        t = tok.type
        if t == "heading_open":
            blocks.append(Block("heading", _inline(tokens[i + 1], cites), level=int(tok.tag[1])))
            i += 3
            continue
        if t in ("bullet_list_open", "ordered_list_open"):
            if not list_stack:
                cur_list = Block("list", ordered=(t == "ordered_list_open"))
                blocks.append(cur_list)
            list_stack.append(t == "ordered_list_open")
        elif t in ("bullet_list_close", "ordered_list_close"):
            list_stack.pop()
            if not list_stack:
                cur_list = None
        elif t == "blockquote_open":
            quote_depth += 1
        elif t == "blockquote_close":
            quote_depth -= 1
        elif t == "paragraph_open":
            runs = _inline(tokens[i + 1], cites)
            if cur_list is not None:
                cur_list.items.append((len(list_stack) - 1, runs))
            elif quote_depth:
                blocks.append(Block("quote", runs))
            else:
                img = next((c for c in (tokens[i + 1].children or []) if c.type == "image"), None)
                if img is not None and len(tokens[i + 1].children or []) == 1:
                    blocks.append(Block("image", text=img.attrs.get("src", ""), runs=[Run(img.content)]))
                else:
                    blocks.append(Block("para", runs))
            i += 3
            continue
        elif t == "table_open":
            header: list[list[Run]] = []
            rows: list[list[list[Run]]] = []
            j = i + 1
            section = None
            row: list[list[Run]] = []
            while tokens[j].type != "table_close":
                tt = tokens[j].type
                if tt == "thead_open":
                    section = "head"
                elif tt == "tbody_open":
                    section = "body"
                elif tt == "tr_open":
                    row = []
                elif tt in ("th_open", "td_open"):
                    row.append(_inline(tokens[j + 1], cites))
                    j += 2
                elif tt == "tr_close":
                    if section == "head":
                        header = row
                    else:
                        rows.append(row)
                j += 1
            blocks.append(Block("table", header=header, rows=rows))
            i = j + 1
            continue
        elif t == "fence":
            info = (tok.info or "").strip().lower()
            if info == "chart":
                blocks.append(Block("chart", spec=parse_chart(tok.content)))
            else:
                blocks.append(Block("code", text=tok.content.rstrip("\n")))
        elif t == "code_block":
            blocks.append(Block("code", text=tok.content.rstrip("\n")))
        elif t == "hr":
            blocks.append(Block("rule"))
        elif t == "html_block":
            m = re.match(r"\s*<!--\s*notes?:\s*(.*?)\s*-->", tok.content, re.DOTALL | re.IGNORECASE)
            if m:
                blocks.append(Block("notes", text=m.group(1).strip()))
        i += 1
    return DocModel(meta, blocks, cites.sources)


# ---------------------------------------------------------------- sources


def describe_sources(ws, sources: list[Source]) -> list[str]:
    """Human-readable reference list entries, resolved against the index / calcs."""
    import json

    from ..index.store import RefError, Store, parse_ref

    out: list[str] = []
    store = Store(ws.index_path, readonly=True) if ws.index_path.exists() else None
    try:
        for s in sources:
            if s.ref.startswith("calc:"):
                path = ws.calcs_dir / f"{s.ref[5:]}.json"
                if path.exists():
                    calc = json.loads(path.read_text())
                    files = ", ".join(calc.get("source_files", [])) or "workspace tables"
                    out.append(f"Calculation {s.ref} over {files}. SQL: {' '.join(calc['sql'].split())}")
                else:
                    out.append(f"Calculation {s.ref} (missing)")
                continue
            try:
                doc_key, anchor = parse_ref(s.ref)
                doc = store.find_doc(doc_key) if store else None
                if doc is None:
                    raise RefError(doc_key)
                loc = human_location(doc.doc_type, anchor) if anchor else ""
                out.append(f"{doc.title} — {doc.path}{', ' + loc if loc else ''}")
            except RefError:
                out.append(f"{s.ref} (unresolved)")
    finally:
        if store:
            store.close()
    return out


def chart_data(ws, spec: dict[str, Any]) -> tuple[list[str], list[tuple[str, list[float]]], str]:
    """Resolve a chart spec to (categories, [(series name, values)], title)."""
    import json

    title = spec.get("title", "")
    if "calc" in spec:
        calc = json.loads((ws.calcs_dir / f"{str(spec['calc']).replace('calc:', '')}.json").read_text())
        cols, rows = calc["columns"], calc["rows"]
    elif spec.get("data"):
        cols, rows = spec["data"][0], [[_num(v) for v in r] for r in spec["data"][1:] if r]
    else:
        raise ValueError("chart needs `calc: <n>` or `data:` followed by CSV lines")
    x = spec.get("x") or cols[0]
    ys = [y.strip() for y in (spec.get("y") or "").split(",") if y.strip()] or [
        c for c in cols if c != x and all(isinstance(r[cols.index(c)], (int, float)) for r in rows)
    ]
    for c in [x, *ys]:
        if c not in cols:
            raise ValueError(f"chart column '{c}' not in {cols}")
    cats = [str(r[cols.index(x)]) for r in rows]
    series = [(y, [float(r[cols.index(y)]) if r[cols.index(y)] is not None else 0.0 for r in rows]) for y in ys]
    return cats, series, title


def _num(v: str) -> Any:
    try:
        return float(v.replace(",", "")) if re.fullmatch(r"-?[\d,]+(\.\d+)?", v.strip()) else v
    except ValueError:
        return v
