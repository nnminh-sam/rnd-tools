"""PDF extraction: text per page (split into parts for long pages) plus detected tables.

Pages without a text layer (scanned images) are reported as warnings; OCR is out of
scope for the engine so that nothing is ever "read" that a human could not select.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import Block, Extraction, Table
from .tabular import coerce_cell

PAGE_SPLIT_CHARS = 3000
# a narrow cell wraps "Status" as "Statu\ns": rejoin a 1–2 letter lowercase tail
_WRAPPED_TAIL = re.compile(
    r"(?<=[a-z])\n(?!(?:a|of|in|to|at|on|by|or|is|it|an|as|be|we|up|no|so|do|if|vs)\b)(?=[a-z]{1,2}\b)"
)


def _cell_text(cell: str | None) -> str:
    return _WRAPPED_TAIL.sub("", cell or "").replace("\n", " ").strip()


def _split_long(text: str, limit: int) -> list[str]:
    parts, cur = [], []
    size = 0
    for line in text.split("\n"):
        if size + len(line) > limit and cur:
            parts.append("\n".join(cur))
            cur, size = [], 0
        cur.append(line)
        size += len(line) + 1
    if cur:
        parts.append("\n".join(cur))
    return parts


def extract(path: Path) -> Extraction:
    import pdfplumber

    blocks: list[Block] = []
    tables: list[Table] = []
    warnings: list[str] = []
    empty_pages: list[int] = []
    with pdfplumber.open(str(path)) as pdf:
        meta_title = (pdf.metadata or {}).get("Title") or ""
        n_pages = len(pdf.pages)
        for p_no, page in enumerate(pdf.pages, start=1):
            text = (page.extract_text() or "").strip()
            if not text:
                empty_pages.append(p_no)
                continue
            parts = [text] if len(text) <= PAGE_SPLIT_CHARS else _split_long(text, PAGE_SPLIT_CHARS // 2)
            for i, part in enumerate(parts, start=1):
                anchor = f"page{p_no}" if len(parts) == 1 else f"page{p_no}.{i}"
                blocks.append(Block(anchor, "page", part, f"Page {p_no}", {"page": p_no}))
            for t_no, raw in enumerate(page.extract_tables() or [], start=1):
                rows = [[_cell_text(c) for c in r] for r in raw]
                rows = [r for r in rows if any(r)]
                if len(rows) >= 2 and len(rows[0]) >= 2:
                    body = [[coerce_cell(c) for c in r] for r in rows[1:]]
                    tables.append(Table(f"Page {p_no} table {t_no}", f"page{p_no}.t{t_no}", rows[0], body))
    if empty_pages:
        warnings.append(
            f"{len(empty_pages)} page(s) without a text layer (scanned?): {', '.join(map(str, empty_pages[:20]))}"
        )
    title = meta_title.strip() or (blocks[0].text.split("\n", 1)[0][:120] if blocks else path.stem)
    return Extraction("pdf", title, blocks, tables, warnings, {"pages": n_pages})
