"""Plain-text formats: Markdown (incl. captured web pages), .txt, .csv and .html."""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path

from . import Block, Extraction, Table
from .tabular import coerce_cell, row_text

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")


def _read(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")  # pragma: no cover


def split_frontmatter(text: str) -> tuple[dict[str, str], int]:
    """Return simple `key: value` frontmatter and the number of lines it occupies."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, 0
    meta: dict[str, str] = {}
    for i in range(1, min(len(lines), 60)):
        if lines[i].strip() == "---":
            return meta, i + 1
        if ":" in lines[i]:
            k, v = lines[i].split(":", 1)
            meta[k.strip()] = v.strip().strip('"')
    return {}, 0


def _pipe_cells(line: str) -> list[str]:
    s = line.strip()
    s = s.removeprefix("|")
    s = s.removesuffix("|")
    return [c.strip() for c in s.split("|")]


def _markdown_blocks(text: str, skip_lines: int = 0) -> tuple[list[Block], list[Table], str]:
    lines = text.split("\n")
    blocks: list[Block] = []
    tables: list[Table] = []
    stack: list[tuple[int, str]] = []
    first_heading = ""
    buf: list[str] = []
    buf_start = 0
    in_code = False

    def section() -> str:
        return " > ".join(t for _, t in stack)

    def flush(end_line: int) -> None:
        nonlocal buf
        if not buf:
            return
        body = "\n".join(buf).strip()
        if body:
            anchor = f"L{buf_start}" if buf_start == end_line else f"L{buf_start}-L{end_line}"
            # pipe table -> Table for SQL
            if len(buf) >= 3 and "|" in buf[0] and _TABLE_SEP.match(buf[1]):
                header = _pipe_cells(buf[0])
                rows = [_pipe_cells(line) for line in buf[2:] if "|" in line]
                tables.append(
                    Table(f"Table at line {buf_start}", anchor, header, [[coerce_cell(c) for c in r] for r in rows])
                )
                body = "\n".join([" | ".join(header)] + [row_text(header, r) for r in rows])
                blocks.append(Block(anchor, "table_row", body, section()))
            else:
                kind = "list" if re.match(r"^\s*([-*+]|\d+[.)])\s", buf[0]) else "para"
                blocks.append(Block(anchor, kind, body, section()))
        buf = []

    for idx in range(skip_lines, len(lines)):
        line_no = idx + 1
        line = lines[idx]
        if line.strip().startswith("```"):
            in_code = not in_code
        m = None if in_code else _HEADING.match(line)
        if m:
            flush(line_no - 1)
            level, htext = len(m.group(1)), m.group(2).strip()
            first_heading = first_heading or htext
            stack = [(lv, t) for lv, t in stack if lv < level] + [(level, htext)]
            blocks.append(Block(f"L{line_no}", "heading", htext, section(), {"level": level}))
            continue
        if not line.strip() and not in_code:
            flush(line_no - 1)
            continue
        if not buf:
            buf_start = line_no
        buf.append(line)
    flush(len(lines))
    return blocks, tables, first_heading


def extract_markdown(path: Path) -> Extraction:
    text = _read(path)
    meta, skip = split_frontmatter(text)
    blocks, tables, first_heading = _markdown_blocks(text, skip)
    title = meta.get("title") or first_heading or path.stem
    return Extraction(
        "md",
        title,
        blocks,
        tables,
        meta={k: v for k, v in meta.items() if k in ("url", "fetched_at", "source", "title", "author", "date")},
    )


def extract_plain(path: Path) -> Extraction:
    blocks, tables, _ = _markdown_blocks(_read(path))
    for b in blocks:  # a .txt has no markdown semantics
        if b.kind == "heading":
            b.kind = "para"
    return Extraction("txt", path.stem, blocks, tables)


def extract_csv(path: Path) -> Extraction:
    text = _read(path)
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows = [r for r in csv.reader(io.StringIO(text), dialect) if any(c.strip() for c in r)]
    if not rows:
        return Extraction("csv", path.stem, [], warnings=["empty CSV"])
    header = [h.strip() or f"col{i + 1}" for i, h in enumerate(rows[0])]
    blocks = [Block("R1", "row", "Columns: " + ", ".join(header), path.stem)]
    for i, r in enumerate(rows[1:], start=2):
        blocks.append(Block(f"R{i}", "row", row_text(header, r), path.stem, {"r": i}))
    body = [[coerce_cell(c) for c in (r + [""] * len(header))[: len(header)]] for r in rows[1:]]
    return Extraction("csv", path.stem, blocks, [Table(path.stem, f"R1:R{len(rows)}", header, body)])


def extract_html(path: Path) -> Extraction:
    import trafilatura

    html = _read(path)
    md = trafilatura.extract(html, output_format="markdown", include_tables=True, include_links=False) or ""
    meta = trafilatura.extract_metadata(html)
    blocks, tables, first_heading = _markdown_blocks(md)
    title = (meta.title if meta and meta.title else "") or first_heading or path.stem
    warnings = [] if md else ["no main text found in HTML"]
    return Extraction("html", title, blocks, tables, warnings)
