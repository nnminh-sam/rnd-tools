"""Workspace discovery and configuration.

A workspace is any folder containing `.rnd/config.json` (found like `.git/`). All
derived state lives in `.rnd/`; source documents are never modified by indexing.
"""

from __future__ import annotations

import copy
import fnmatch
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MARKER = ".rnd"
CONFIG_NAME = "config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "name": "",
    "extensions": [".docx", ".xlsx", ".xlsm", ".pptx", ".pdf", ".md", ".txt", ".csv", ".html", ".htm"],
    "exclude": [
        ".rnd/**",
        ".claude/**",
        ".git/**",
        "outputs/**",
        "**/.raw/**",
        "node_modules/**",
        "**/~$*",
        "**/.~lock*",
        "**/.DS_Store",
        "CLAUDE.md",
        "TUTORIAL.md",
        "README.md",
    ],
    "chunk_chars": 1800,
    "semantic": False,
    "semantic_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    # Per-sheet overrides, e.g. {"sources/data.xlsx::Results": {"header_row": 4}}
    "tables": {},
}


class WorkspaceError(RuntimeError):
    pass


@dataclass
class Workspace:
    root: Path
    config: dict[str, Any] = field(default_factory=dict)

    @property
    def rnd_dir(self) -> Path:
        return self.root / MARKER

    @property
    def index_path(self) -> Path:
        return self.rnd_dir / "index.sqlite"

    @property
    def data_path(self) -> Path:
        return self.rnd_dir / "data.duckdb"

    @property
    def calcs_dir(self) -> Path:
        return self.rnd_dir / "calcs"

    @property
    def packs_dir(self) -> Path:
        return self.rnd_dir / "packs"

    @property
    def backups_dir(self) -> Path:
        return self.rnd_dir / "backups"

    @property
    def name(self) -> str:
        return self.config.get("name") or self.root.name

    def rel(self, path: Path | str) -> str:
        p = Path(path)
        if not p.is_absolute():
            p = self.root / p
        try:
            return p.resolve().relative_to(self.root.resolve()).as_posix()
        except ValueError:
            return p.as_posix()

    def abspath(self, rel: str | Path) -> Path:
        p = Path(rel)
        return p if p.is_absolute() else (self.root / p)

    def is_excluded(self, rel_path: str) -> bool:
        return any(fnmatch.fnmatch(rel_path, pat) for pat in self.config.get("exclude", []))

    def iter_source_files(self) -> list[Path]:
        exts = {e.lower() for e in self.config.get("extensions", [])}
        files: list[Path] = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            rel_dir = Path(dirpath).relative_to(self.root).as_posix()
            # prune hidden and excluded directories early
            dirnames[:] = [
                d
                for d in dirnames
                if not d.startswith(".") and not self.is_excluded((d if rel_dir == "." else f"{rel_dir}/{d}") + "/")
            ]
            for fn in filenames:
                rel = f"{rel_dir}/{fn}" if rel_dir != "." else fn
                if (
                    Path(fn).suffix.lower() in exts
                    and not self.is_excluded(rel)
                    and not is_chat_export(self.root / rel)
                ):
                    files.append(self.root / rel)
        return sorted(files)

    def save_config(self) -> None:
        (self.rnd_dir / CONFIG_NAME).write_text(json.dumps(self.config, indent=2, ensure_ascii=False) + "\n")


def is_chat_export(path: Path) -> bool:
    """An exported Claude Code conversation (/export) is not a source: indexing it would let
    agents cite earlier chat answers as evidence."""
    if path.suffix.lower() not in (".txt", ".md"):
        return False
    try:
        with open(path, "rb") as f:
            head = f.read(600).decode("utf-8", "replace")
    except OSError:
        return False
    return "Claude Code v" in head and ("▐" in head or "❯" in head or "⏺" in head)


def _load_config(rnd_dir: Path) -> dict[str, Any]:
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    path = rnd_dir / CONFIG_NAME
    if path.exists():
        user = json.loads(path.read_text() or "{}")
        cfg.update(user)
    return cfg


def find_workspace(start: Path | str | None = None) -> Workspace:
    """Locate the workspace containing `start` (default: $RND_WORKSPACE or cwd)."""
    base = Path(start or os.environ.get("RND_WORKSPACE") or os.getcwd()).resolve()
    for cand in [base, *base.parents]:
        # config.json, not just the folder: a stray `outputs/.rnd/` (an agent writing a
        # relative path from the wrong cwd) must not be mistaken for a workspace
        if (cand / MARKER / CONFIG_NAME).is_file():
            return Workspace(cand, _load_config(cand / MARKER))
    raise WorkspaceError(
        f"No RnD workspace found at or above {base}. Run `/rnd:setup` (or `rnd init`) in your project folder."
    )


def find_workspace_or_none(start: Path | str | None = None) -> Workspace | None:
    try:
        return find_workspace(start)
    except WorkspaceError:
        return None


def init_workspace(root: Path | str, name: str | None = None, semantic: bool = False) -> Workspace:
    root = Path(root).resolve()
    rnd_dir = root / MARKER
    rnd_dir.mkdir(parents=True, exist_ok=True)
    cfg = _load_config(rnd_dir)
    cfg["name"] = name or cfg.get("name") or root.name
    cfg["semantic"] = bool(semantic or cfg.get("semantic"))
    ws = Workspace(root, cfg)
    for d in (ws.calcs_dir, ws.packs_dir, ws.backups_dir):
        d.mkdir(exist_ok=True)
    for d in ("sources", "notes", "outputs"):
        (root / d).mkdir(exist_ok=True)
    ws.save_config()
    gitignore = rnd_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("index.sqlite*\ndata.duckdb*\nbackups/\n")
    return ws
