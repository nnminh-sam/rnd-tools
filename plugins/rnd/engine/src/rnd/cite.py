"""Citation syntax shared by the verifier and the renderers.

    [@doc-id#anchor]                       cite a location
    [@doc-id#anchor "exact words"]         cite + verbatim quote (checked character for character)
    [@calc:7]                              cite a saved SQL result (.rnd/calcs/7.json)
    [@a#p3; @b#page2 "quote"]              several sources for one claim

Sheet anchors with spaces use Excel quoting: [@tests#'Shell fatigue'!A5:H9]
"""

from __future__ import annotations

import re
from dataclasses import dataclass

CITE_GROUP = re.compile(r"\[@(?P<body>[^\]\n]+)\]")
_ITEM = re.compile(r"""^\s*@?(?P<ref>(?:[^\s"'“”;]|'[^']*')+)(?:\s+["“](?P<quote>[^"”]*)["”])?\s*$""")


@dataclass(frozen=True)
class Citation:
    ref: str
    quote: str | None = None

    @property
    def is_calc(self) -> bool:
        return self.ref.startswith("calc:")

    @property
    def calc_id(self) -> int:
        return int(self.ref.split(":", 1)[1])


def _split_items(body: str) -> list[str]:
    items, cur, in_q = [], [], False
    for ch in body:
        if ch in '"“”':
            in_q = not in_q if ch == '"' else (ch == "“")
        if ch == ";" and not in_q:
            items.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    items.append("".join(cur))
    return [i for i in items if i.strip()]


def parse_group(body: str) -> tuple[list[Citation], list[str]]:
    """Parse the inside of one [@...] group. Returns (citations, malformed items)."""
    cites, bad = [], []
    for item in _split_items(body):
        m = _ITEM.match(item)
        if not m:
            bad.append(item.strip())
            continue
        ref = m.group("ref")
        if ref.startswith("calc:") and not ref[5:].isdigit():
            bad.append(item.strip())
            continue
        cites.append(Citation(ref, m.group("quote")))
    return cites, bad


def find_citations(text: str) -> list[tuple[re.Match[str], list[Citation], list[str]]]:
    return [(m, *parse_group(m.group("body"))) for m in CITE_GROUP.finditer(text)]


def strip_citations(text: str) -> str:
    return CITE_GROUP.sub("", text)
