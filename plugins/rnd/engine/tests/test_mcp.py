"""The MCP adapter: engine errors must reach the model as readable messages."""

import anyio
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from rnd import mcp_server


def call(name: str, args: dict):
    return anyio.run(mcp_server.mcp.call_tool, name, args)


@pytest.fixture()
def server_ws(fresh_ws, monkeypatch):
    monkeypatch.setitem(mcp_server._current, "root", fresh_ws.root)
    return fresh_ws


def test_sql_error_names_the_problem(server_ws):
    with pytest.raises(ToolError, match="nope"):
        call("sql", {"query": "select nope from seat_shell_materials_test_results__shell_fatigue"})


def test_render_refusal_explains_why(server_ws):
    draft = server_ws.root / "outputs" / "draft.md"
    draft.write_text("# Draft\n\nOnline share is 65% [@home-office-seating-market-brief-2026#page2].\n")
    with pytest.raises(ToolError, match="figure-mismatch"):
        call("render", {"path": "outputs/draft.md", "format": "docx"})


def test_verify_missing_file_is_reported(server_ws):
    with pytest.raises(ToolError, match=r"missing\.md"):
        call("verify", {"path": "outputs/missing.md"})


def test_status_prints_absolute_write_locations(server_ws):
    res = call("status", {})
    text = res.content[0].text if hasattr(res, "content") else str(res)
    assert str(server_ws.packs_dir) in text


def test_verify_refuses_files_outside_the_workspace(server_ws, tmp_path_factory):
    outside = tmp_path_factory.mktemp("elsewhere") / "x.md"
    outside.write_text("# x\n")
    with pytest.raises(ToolError, match="outside the workspace"):
        call("verify", {"path": str(outside)})


def test_search_names_the_exact_row_to_cite(server_ws):
    res = call("search", {"queries": ["seat shell fatigue target cycles"], "k": 3})
    assert "cite: 2026-02-09-kickoff-project-kestrel#t1.r10" in res.content[0].text
