"""Static checks of the Claude Code layer (skills, agents).

Each guards a mistake that tests of the engine cannot see and that only shows up in a
live session as wasted Opus tokens or a failed step.
"""

import json
import re
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[2]
SKILLS = sorted((PLUGIN / "skills").glob("*/SKILL.md"))
AGENT_FILES = sorted((PLUGIN / "agents").glob("*.md"))
AGENTS = {p.stem for p in AGENT_FILES}


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text()
    block = text.split("---", 2)[1]
    return {k.strip(): v.strip().strip('"') for k, v in re.findall(r"^([\w-]+):(.*)$", block, re.MULTILINE)}


@pytest.mark.parametrize("skill", [p for p in SKILLS if frontmatter(p).get("context") == "fork"], ids=str)
def test_forked_skills_pin_a_plugin_agent_and_a_model(skill):
    fm = frontmatter(skill)
    # a bare `agent: librarian` does not match the plugin agent `rnd:librarian`: Claude Code
    # silently falls back to general-purpose on the session model (often Opus)
    assert fm["agent"].startswith("rnd:") and fm["agent"][4:] in AGENTS, fm["agent"]
    assert fm.get("model") in {"haiku", "sonnet", "opus"}
    assert fm.get("background") == "false"


@pytest.mark.parametrize("skill", SKILLS, ids=str)
def test_orchestrating_skills_run_agents_in_the_foreground(skill):
    body = skill.read_text()
    launches = re.findall(r"`rnd:(librarian|analyst|writer|ideator|strategist|auditor|scout)`", body)
    if launches and frontmatter(skill).get("context") != "fork":
        # background agents report back after the skill's turn, which then runs on the
        # session model instead of the skill's `model:`
        assert "run_in_background: false" in body


@pytest.mark.parametrize("path", [*SKILLS, *AGENT_FILES], ids=str)
def test_no_file_name_that_claude_code_blocks_for_agents(path):
    # Claude Code refuses Write from subagents for basenames matching
    # ^(REPORT|SUMMARY|FINDINGS|ANALYSIS).*\.md$ (case-insensitive)
    blocked = re.compile(r"(?:outputs|packs)/(?:analysis|report|summary|findings)[^/\s`]*\.md", re.IGNORECASE)
    assert not blocked.search(path.read_text())


@pytest.mark.parametrize("skill", SKILLS, ids=str)
def test_skills_reference_existing_agents(skill):
    for name in re.findall(r"`rnd:([a-z]+)`", skill.read_text()):
        assert name in AGENTS, name


# ---------------------------------------------------------------- packaging for GitHub installs

REPO = PLUGIN.parents[1]


def test_marketplace_entry_points_at_this_plugin():
    if not (REPO / ".claude-plugin" / "marketplace.json").exists():
        pytest.skip("installed copy of the plugin, not the repository")
    market = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    (entry,) = [p for p in market["plugins"] if p["name"] == manifest["name"]]
    assert (REPO / entry["source"]).resolve() == PLUGIN.resolve()
    assert "version" not in entry  # plugin.json is the single source of the version


def test_versions_agree_so_users_receive_updates():
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    pyproject = (PLUGIN / "engine" / "pyproject.toml").read_text()
    version = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE).group(1)
    lock = (PLUGIN / "engine" / "uv.lock").read_text()
    assert manifest["version"] == version
    # the plugin runs `uv run --frozen`: the lock must describe the current project
    assert f'name = "rnd"\nversion = "{version}"' in lock


def test_engine_launch_is_frozen_and_skips_dev_tools():
    launches = [json.loads((PLUGIN / ".mcp.json").read_text())["mcpServers"]["rnd"]["args"]]
    for matchers in json.loads((PLUGIN / "hooks" / "hooks.json").read_text())["hooks"].values():
        launches += [h["args"] for m in matchers for h in m["hooks"]]
    for args in launches:
        assert {"--frozen", "--no-dev"} <= set(args), args
        assert args[args.index("--project") + 1] == "${CLAUDE_PLUGIN_ROOT}/engine"


def test_no_workspace_files_ship_inside_the_plugin():
    # a CLAUDE.md or .claude/ in the plugin tree was created by running `rnd init` in the
    # wrong folder; it would be copied to every user's plugin cache
    stray = [p for p in PLUGIN.rglob("*") if p.name in ("CLAUDE.md", ".claude") and ".venv" not in p.parts]
    assert not stray, stray
