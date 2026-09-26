"""Shared fixtures: one indexed copy of the KESTREL demo per test session."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1]
DEMO = ENGINE.parent / "demo" / "kestrel-chair"
GOLDEN = Path(__file__).parent / "golden" / "kestrel.json"


@pytest.fixture(scope="session")
def golden() -> dict:
    return json.loads(GOLDEN.read_text())


@pytest.fixture(scope="session")
def ws(tmp_path_factory):
    from rnd.index.indexer import index_workspace
    from rnd.workspace import init_workspace

    root = tmp_path_factory.mktemp("kestrel")
    shutil.copytree(DEMO, root, dirs_exist_ok=True)
    workspace = init_workspace(root, "KESTREL")
    report = index_workspace(workspace)
    assert not report.failed, report.failed
    return workspace


@pytest.fixture()
def fresh_ws(tmp_path):
    """A writable, indexed workspace for tests that modify files."""
    from rnd.index.indexer import index_workspace
    from rnd.workspace import init_workspace

    shutil.copytree(DEMO, tmp_path, dirs_exist_ok=True)
    workspace = init_workspace(tmp_path, "KESTREL")
    index_workspace(workspace)
    return workspace
