"""Capture web sources verbatim into the workspace so they can be cited and verified.

Claude Code's WebFetch returns a model-written summary of a page, which cannot be
quoted reliably. `capture` stores the page's main text as Markdown with provenance
frontmatter (url, fetched_at, sha256 of the raw response) and keeps the raw HTML in
`.raw/` for audit. PDFs and Office files are downloaded as-is. robots.txt is honoured.
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

from .util import now_iso, slugify
from .workspace import Workspace

USER_AGENT = "RnD-capture/0.1 (+research tool; respects robots.txt)"
MAX_BYTES = 30 * 1024 * 1024
BINARY_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "text/csv": ".csv",
}


@dataclass
class Captured:
    url: str
    path: str | None
    title: str = ""
    error: str | None = None


def _allowed(client, url: str, cache: dict[str, RobotFileParser | None]) -> bool:
    parts = urlparse(url)
    base = f"{parts.scheme}://{parts.netloc}"
    if base not in cache:
        rp = RobotFileParser()
        try:
            r = client.get(base + "/robots.txt", timeout=10)
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
            cache[base] = rp
        except Exception:
            cache[base] = None  # unreachable robots.txt: treat as allowed
    rp = cache[base]
    return True if rp is None else rp.can_fetch(USER_AGENT, url)


def _links(html: str, base_url: str) -> list[str]:
    host = urlparse(base_url).netloc
    out = []
    for href in re.findall(r"""<a\s[^>]*href=["']([^"'#]+)""", html, re.IGNORECASE):
        u = urljoin(base_url, href)
        if urlparse(u).netloc == host and u.startswith("http") and u not in out:
            out.append(u)
    return out


def _unique_path(folder: Path, stem: str, suffix: str) -> Path:
    p = folder / f"{stem}{suffix}"
    n = 2
    while p.exists():
        p = folder / f"{stem}-{n}{suffix}"
        n += 1
    return p


def capture(
    ws: Workspace, urls: list[str], folder: str = "sources/web", follow_links: int = 0, delay_s: float = 1.0
) -> list[Captured]:
    import httpx
    import trafilatura

    dest = ws.abspath(folder)
    (dest / ".raw").mkdir(parents=True, exist_ok=True)
    results: list[Captured] = []
    robots: dict[str, RobotFileParser | None] = {}
    queue = [(u.strip(), 0) for u in urls if u.strip()]
    seen: set[str] = set()
    extra_budget = max(0, follow_links)
    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=30) as client:
        while queue:
            url, depth = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            if not url.startswith(("http://", "https://")):
                results.append(Captured(url, None, error="only http(s) URLs are supported"))
                continue
            if not _allowed(client, url, robots):
                results.append(Captured(url, None, error="disallowed by robots.txt"))
                continue
            try:
                resp = client.get(url)
                resp.raise_for_status()
            except Exception as exc:
                results.append(Captured(url, None, error=f"{type(exc).__name__}: {exc}"[:200]))
                continue
            raw = resp.content
            if len(raw) > MAX_BYTES:
                results.append(Captured(url, None, error=f"larger than {MAX_BYTES // 1_048_576} MB"))
                continue
            ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
            parsed = urlparse(str(resp.url))
            stem = slugify(f"{parsed.netloc}-{parsed.path}", max_len=70)
            digest = hashlib.sha256(raw).hexdigest()
            suffix = BINARY_TYPES.get(ctype) or next(
                (s for s in BINARY_TYPES.values() if parsed.path.lower().endswith(s)), None
            )
            if suffix:
                path = _unique_path(dest, stem, suffix)
                path.write_bytes(raw)
                (dest / ".raw" / f"{path.name}.source.txt").write_text(
                    f"url: {resp.url}\nfetched_at: {now_iso()}\nsha256: {digest}\n"
                )
                results.append(Captured(str(resp.url), ws.rel(path), path.name))
            else:
                html = resp.text
                md = (
                    trafilatura.extract(
                        html, output_format="markdown", include_tables=True, include_links=False, favor_precision=True
                    )
                    or ""
                )
                meta = trafilatura.extract_metadata(html)
                title = (meta.title if meta and meta.title else "") or stem
                if not md.strip():
                    results.append(
                        Captured(str(resp.url), None, title, "no main text found (page may need JavaScript)")
                    )
                    continue
                path = _unique_path(dest, stem, ".md")
                front = [
                    "---",
                    f"title: {title.replace(chr(10), ' ')}",
                    f"url: {resp.url}",
                    f"fetched_at: {now_iso()}",
                    f"sha256: {digest}",
                ]
                if meta and meta.date:
                    front.append(f"date: {meta.date}")
                if meta and meta.author:
                    front.append(f"author: {meta.author}")
                front.append("---")
                path.write_text("\n".join(front) + "\n\n" + md.strip() + "\n", encoding="utf-8")
                (dest / ".raw" / f"{path.stem}.html").write_bytes(raw)
                results.append(Captured(str(resp.url), ws.rel(path), title))
                if depth == 0 and extra_budget:
                    for link in _links(html, str(resp.url)):
                        if extra_budget <= 0:
                            break
                        if link not in seen:
                            queue.append((link, 1))
                            extra_budget -= 1
            time.sleep(delay_s)
    return results


def format_results(results: list[Captured]) -> str:
    ok = [r for r in results if r.path]
    lines = [f"Captured {len(ok)} of {len(results)} URL(s)."]
    for r in results:
        if r.path:
            lines.append(f"  OK   {r.path}  ← {r.url}  ({r.title[:60]})")
        else:
            lines.append(f"  FAIL {r.url}: {r.error}")
    return "\n".join(lines)
