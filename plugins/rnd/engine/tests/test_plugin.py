"""Static checks of the Claude Code layer (skills, agents).

Each guards a mistake that tests of the engine cannot see and that only shows up in a
live session as wasted Opus tokens or a failed step.
"""

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
