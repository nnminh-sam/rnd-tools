"""Word (.docx) extraction: paragraphs, headings, lists and tables in document order."""

from __future__ import annotations

import re
from pathlib import Path

from . import Block, Extraction, Table
from .tabular import coerce_cell, row_text

_HEADING_RE = re.compile(r"^heading\s*(\d)$", re.IGNORECASE)


def _heading_level(paragraph) -> int | None:
    style = paragraph.style
    # style_id is language-independent ("Heading1"); name may be localised.
    for label in (getattr(style, "style_id", "") or "", getattr(style, "name", "") or ""):
        m = _HEADING_RE.match(label.strip())
        if m:
            return int(m.group(1))
        if label.lower() == "title":
            return 0
    ppr = paragraph._p.pPr
    if ppr is not None:
        lvl = ppr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}outlineLvl")
        if lvl is not None:
            val = lvl.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val")
            if val is not None and val.isdigit() and int(val) < 9:
                return int(val) + 1
    return None


def _is_list(paragraph) -> bool:
    name = (getattr(paragraph.style, "name", "") or "").lower()
    if "list" in name:
        return True
    ppr = paragraph._p.pPr
    return ppr is not None and ppr.numPr is not None


def _table_rows(table) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table.rows:
        cells, seen = [], set()
        for cell in row.cells:
            if id(cell._tc) in seen:  # horizontally merged cell repeats
                continue
            seen.add(id(cell._tc))
            cells.append(" ".join(p.text.strip() for p in cell.paragraphs if p.text.strip()))
        rows.append(cells)
    return rows


def extract(path: Path) -> Extraction:
    import docx  # python-docx

    document = docx.Document(str(path))
    blocks: list[Block] = []
    tables: list[Table] = []
    heading_stack: list[tuple[int, str]] = []
    title = (document.core_properties.title or "").strip()
    p_no = t_no = 0

    def section() -> str:
        return " > ".join(text for _, text in heading_stack)

    for item in document.iter_inner_content():
        if item.__class__.__name__ == "Paragraph":
            text = item.text.strip()
            if not text:
                continue
            p_no += 1
            level = _heading_level(item)
            if level is not None:
                if level == 0 and not title:
                    title = text
                lvl = max(level, 1)
                heading_stack = [(lv, tx) for lv, tx in heading_stack if lv < lvl] + [(lvl, text)]
                blocks.append(Block(f"p{p_no}", "heading", text, section(), {"level": level}))
                continue
            kind = "list" if _is_list(item) else "para"
            shown = f"- {text}" if kind == "list" else text
            blocks.append(Block(f"p{p_no}", kind, shown, section()))
        else:  # Table
            t_no += 1
            rows = [r for r in _table_rows(item) if any(c for c in r)]
            if not rows:
                continue
            header = rows[0]
            for r_idx, row in enumerate(rows, start=1):
                txt = " | ".join(row) if r_idx == 1 else row_text(header, row)
                blocks.append(Block(f"t{t_no}.r{r_idx}", "table_row", txt, section(), {"table": t_no}))
            if len(rows) >= 2 and len(header) >= 2:
                width = len(header)
                body = [[coerce_cell(c) for c in (r + [""] * width)[:width]] for r in rows[1:]]
                tables.append(Table(f"Table {t_no}", f"t{t_no}", header, body))

    if not title:
        first = next((b.text for b in blocks if b.kind == "heading"), "")
        title = first or path.stem
    return Extraction("docx", title, blocks, tables, meta={"paragraphs": p_no, "tables": t_no})
