"""The repository's commit-msg hook (.githooks/commit-msg) and its documented convention."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
HOOK = REPO / ".githooks" / "commit-msg"

pytestmark = [
    pytest.mark.skipif(not HOOK.exists(), reason="installed copy of the plugin, not the repository"),
    pytest.mark.skipif(shutil.which("sh") is None, reason="needs a POSIX shell"),
]


def check(tmp_path: Path, message: str) -> tuple[bool, str]:
    msg = tmp_path / "COMMIT_EDITMSG"
    msg.write_text(message)
    res = subprocess.run(["sh", str(HOOK), str(msg)], capture_output=True, text=True)
    return res.returncode == 0, res.stderr


@pytest.mark.parametrize(
    "message",
    [
        "feat(skill): new data crawling skill\n\n- add /rnd:crawl\n- index captured pages on save\n",
        "fix(skill/ask,verify): cite exact rows\n\n- search names the row to cite\n  and verify warns on broad refs\n",
        "hot-fix(plugin): README install command\n\n- fix the marketplace add command\n",
        "chore(repo): commit convention\n\n- add the hook\n# a comment\n# ------------------------ >8 ------------------------\ndiff\n",
        "Merge branch 'feature'\n",
        "fixup! feat(skill): new data crawling skill\n",
    ],
)
def test_valid_messages_pass(tmp_path, message):
    ok, err = check(tmp_path, message)
    assert ok, err


@pytest.mark.parametrize(
    "message,reason",
    [
        ("update skills\n\n- x\n", "header must be"),
        ("docs(docs): x\n\n- y\n", 'type "docs"'),
        ("feat(skills): x\n\n- y\n", 'scope "skills"'),
        ("feat(): x\n\n- y\n", "scope is empty"),
        ("fix(engine): Fix the thing\n\n- y\n", "lower case"),
        ("fix(engine): the thing.\n\n- y\n", "full stop"),
        ("fix(engine): the thing\n", "add a body"),
        ("fix(engine): the thing\n- y\n", "blank line"),
        ("fix(engine): the thing\n\nThis fixes it.\n", "not a bullet"),
        ("fix(engine): the thing\n\n- y\n\nCo-Authored-By: A <a@b.c>\n", "Co-Authored-By"),
        ("feat(skill): " + "x" * 70 + "\n\n- y\n", "within 72"),
    ],
)
def test_invalid_messages_are_rejected_with_a_reason(tmp_path, message, reason):
    ok, err = check(tmp_path, message)
    assert not ok and reason in err, err


def test_documented_scopes_match_the_hook():
    hook_scopes = set(re.search(r'^SCOPES="([^"]+)"', HOOK.read_text(), re.MULTILINE).group(1).split())
    table = (REPO / "CONTRIBUTING.md").read_text().split("| Scope | Component |", 1)[1].split("\n\n", 1)[0]
    doc_scopes = set(re.findall(r"^\| `([a-z]+)` \|", table, re.MULTILINE))
    assert doc_scopes == hook_scopes
    template = (REPO / ".gitmessage").read_text()
    assert all(scope in template for scope in hook_scopes)
