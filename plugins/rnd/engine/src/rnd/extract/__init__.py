"""Deterministic extractors: file -> addressable blocks + tabular data.

Every block carries an *anchor* that a human can find in the original file:

    docx  p12 (12th non-empty paragraph), t2.r3 (table 2, row 3)
    xlsx  Results!A5:H5 (a row), quoted as 'Sheet name'!A5:H5 when it has spaces
    pptx  s5 (slide 5 text), s5.t1 (table), s5.c1 (chart data), s5.notes
    pdf   page3 (or page3.1, page3.2 for long pages)
    md    L10-L14 (line range);  csv  R7 (line 7)

Anchors are the contract between extraction, search results, citations and the
verifier. Change them only with a schema version bump (see index/store.py).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Block:
    anchor: str
    kind: str  # heading | para | list | table_row | row | slide | notes | chart | page | line
    text: str
    section: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Table:
    """A rectangular table that becomes a SQL table in the data layer."""

    name: str  # sheet name, "Table 2", "Slide 4 table 1" ...
    anchor: str  # where it lives in the source, e.g. "Results!A3:H27"
    columns: list[str]
    rows: list[list[Any]]
    header_row: int | None = None  # 1-based sheet row of the header (xlsx)
    first_col: int = 1  # 1-based sheet column of the first column (xlsx)
    notes: list[str] = field(default_factory=list)


@dataclass
class Extraction:
    doc_type: str
    title: str
    blocks: list[Block]
    tables: list[Table] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


Extractor = Callable[[Path], Extraction]


def _registry() -> dict[str, tuple[str, Extractor]]:
    # Imported lazily so that light-weight callers (hooks, verifier) never pay for
    # python-docx / pdfplumber import time.
    from . import excel, pdf, powerpoint, text, word

    return {
        ".docx": ("docx", word.extract),
        ".xlsx": ("xlsx", excel.extract),
        ".xlsm": ("xlsx", excel.extract),
        ".pptx": ("pptx", powerpoint.extract),
        ".pdf": ("pdf", pdf.extract),
        ".md": ("md", text.extract_markdown),
        ".txt": ("txt", text.extract_plain),
        ".csv": ("csv", text.extract_csv),
        ".html": ("html", text.extract_html),
        ".htm": ("html", text.extract_html),
    }


def doc_type_for(path: Path) -> str | None:
    entry = _registry().get(path.suffix.lower())
    return entry[0] if entry else None


def extract(path: Path) -> Extraction:
    entry = _registry().get(path.suffix.lower())
    if entry is None:
        raise ValueError(f"Unsupported file type: {path.suffix}")
    return entry[1](path)
