"""Hook handlers: JSON in, JSON out, silent outside workspaces, light imports."""

import io
import json
import shutil
import subprocess
import sys

import pytest

from rnd import hooks


def run_hook(monkeypatch, capsys, handler, payload):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    handler(payload)
    out = capsys.readouterr().out
    return json.loads(out) if out else None


def test_pre_read_denies_office_files_with_doc_id(ws, monkeypatch, capsys):
    path = str(ws.root / "sources/engineering/TR-2026-031 P2 prototype test report.pdf")
    out = run_hook(monkeypatch, capsys, hooks.pre_read, {"tool_input": {"file_path": path}})
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "tr-2026-031-p2-prototype-test-report" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_pre_read_ignores_other_files_and_other_folders(ws, tmp_path, monkeypatch, capsys):
    assert (
        run_hook(monkeypatch, capsys, hooks.pre_read, {"tool_input": {"file_path": str(ws.root / "README.md")}}) is None
    )
    outside = tmp_path / "x.pdf"
    outside.write_bytes(b"%PDF-1.4")
    assert run_hook(monkeypatch, capsys, hooks.pre_read, {"tool_input": {"file_path": str(outside)}}) is None


def test_post_write_blocks_failed_verification(ws, monkeypatch, capsys):
    path = ws.root / "outputs" / "draft.md"
    path.write_text("Online share is 65% [@home-office-seating-market-brief-2026#page2].\n")
    out = run_hook(monkeypatch, capsys, hooks.post_write, {"tool_input": {"file_path": str(path)}})
    assert out["decision"] == "block" and "figure-mismatch" in out["reason"]
    path.write_text("Online share is 62% [@home-office-seating-market-brief-2026#page2].\n")
    out = run_hook(monkeypatch, capsys, hooks.post_write, {"tool_input": {"file_path": str(path)}})
    assert "RnD verify PASS" in out["hookSpecificOutput"]["additionalContext"]


def test_session_start_coaches_opus_users(ws, monkeypatch, capsys):
    out = run_hook(monkeypatch, capsys, hooks.session_start, {"cwd": str(ws.root), "model": "claude-opus-5-5"})
    assert "11 documents indexed" in out["hookSpecificOutput"]["additionalContext"]
    assert "Opus" in out["systemMessage"]
    out = run_hook(monkeypatch, capsys, hooks.session_start, {"cwd": str(ws.root), "model": "claude-sonnet-5"})
    assert "systemMessage" not in out


@pytest.mark.parametrize(
    "prompt,command",
    [
        ("Can you make slides about the P2 results?", "/rnd:deck"),
        ("What is the average cycles to failure per material?", "/rnd:analyze"),
        ("Which competitor chairs have flip-up armrests?", "/rnd:ask"),
        ("Should we go with option B or C for the armrest?", "/rnd:decide"),
    ],
)
def test_prompt_routing(ws, monkeypatch, capsys, prompt, command):
    out = run_hook(monkeypatch, capsys, hooks.prompt, {"cwd": str(ws.root), "prompt": prompt, "session_id": "t"})
    assert command in out["hookSpecificOutput"]["additionalContext"]


def test_prompt_ignores_background_agent_notifications(ws, monkeypatch, capsys):
    note = "<task-notification> <task-id>a1</task-id> <status>completed</status> <summary>Agent report done"
    assert run_hook(monkeypatch, capsys, hooks.prompt, {"cwd": str(ws.root), "prompt": note, "session_id": "t"}) is None


def test_prompt_warns_once_when_session_switched_to_opus(ws, tmp_path, monkeypatch, capsys):
    transcript = tmp_path / "t.jsonl"
    transcript.write_text(json.dumps({"type": "assistant", "message": {"model": "claude-opus-5-5"}}) + "\n")
    payload = {"cwd": str(ws.root), "prompt": "What are the product targets?", "session_id": "opus-s"}
    payload["transcript_path"] = str(transcript)
    out = run_hook(monkeypatch, capsys, hooks.prompt, payload)
    assert "session is on Opus" in out["systemMessage"]
    assert "rnd:librarian" in out["hookSpecificOutput"]["additionalContext"]
    out = run_hook(monkeypatch, capsys, hooks.prompt, payload)
    assert "session is on Opus" not in out.get("systemMessage", "")


def test_post_write_blocks_files_in_a_stray_rnd_folder(ws, monkeypatch, capsys):
    stray = ws.root / "outputs" / ".rnd" / "packs"
    stray.mkdir(parents=True, exist_ok=True)
    path = stray / "decide-x.md"
    path.write_text("# pack\n")
    out = run_hook(monkeypatch, capsys, hooks.post_write, {"tool_input": {"file_path": str(path)}})
    assert out["decision"] == "block" and str(ws.packs_dir) in out["reason"]
    # and the stray folder is not mistaken for a workspace
    from rnd.workspace import find_workspace

    assert find_workspace(stray).root == ws.root
    shutil.rmtree(ws.root / "outputs" / ".rnd")


def test_post_write_blocks_drafts_written_outside_the_workspace(ws, tmp_path, monkeypatch, capsys):
    stray = tmp_path / "elsewhere" / "outputs"
    stray.mkdir(parents=True)
    path = stray / "figures-x.md"
    path.write_text("# x\n")
    payload = {"cwd": str(ws.root), "tool_input": {"file_path": str(path)}}
    out = run_hook(monkeypatch, capsys, hooks.post_write, payload)
    assert out["decision"] == "block" and str(ws.root / "outputs" / "figures-x.md") in out["reason"]


def test_hooks_and_verifier_import_light():
    code = (
        "import sys, rnd.hooks, rnd.verify; "
        "heavy = [m for m in ('docx', 'openpyxl', 'pptx', 'pdfplumber', 'duckdb', 'reportlab', 'trafilatura') "
        "if m in sys.modules]; print(heavy)"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout.strip()
    assert out == "[]"
