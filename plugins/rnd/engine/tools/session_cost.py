"""Which agents and models did a Claude Code session really use, and what did each cost?

    uv run python tools/session_cost.py ~/.claude/projects/<folder>/<session-id>.jsonl

Reads the main transcript and its `<session-id>/subagents/agent-*.jsonl` (+ `.meta.json`)
and prints cost per agent type and model at list prices. This is how the v0.1 routing bugs
were found: forked skills showing up as `general-purpose` on Opus.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

# USD per million tokens (input, output); cache reads 0.1x input, cache writes 2x input (Claude
# Code uses the 1-hour cache TTL); `claude -p --output-format json` reports the exact total
PRICES = {"opus": (4.0, 20.0), "sonnet": (2.0, 10.0), "haiku": (1.0, 5.0)}


def _price(model: str) -> tuple[float, float]:
    return next((p for k, p in PRICES.items() if k in model), (0.0, 0.0))


def _cost(model: str, usage: dict) -> float:
    i, o = _price(model)
    return (
        usage.get("input_tokens", 0) * i
        + usage.get("output_tokens", 0) * o
        + usage.get("cache_read_input_tokens", 0) * i * 0.1
        + usage.get("cache_creation_input_tokens", 0) * i * 2.0
    ) / 1e6


def _tally(path: Path, label: str, totals: Counter, seen: set[str]) -> None:
    for line in path.read_text().splitlines():
        rec = json.loads(line)
        if rec.get("type") != "assistant":
            continue
        msg = rec["message"]
        if msg.get("id") in seen or msg.get("model", "").startswith("<"):
            continue
        seen.add(msg.get("id"))
        totals[(label, msg.get("model", "?"))] += _cost(msg.get("model", ""), msg.get("usage", {}))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main_path = Path(sys.argv[1]).expanduser()
    totals: Counter = Counter()
    seen: set[str] = set()
    _tally(main_path, "main session", totals, seen)
    for sub in sorted((main_path.parent / main_path.stem / "subagents").glob("agent-*.jsonl")):
        meta_path = sub.with_suffix(".meta.json")
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        _tally(sub, meta.get("agentType", "?"), totals, seen)
    grand = sum(totals.values()) or 1.0
    print(f"{'agent':34} {'model':28} {'USD':>7} {'share':>6}")
    for (label, model), usd in totals.most_common():
        print(f"{label:34} {model:28} {usd:7.2f} {100 * usd / grand:5.1f}%")
    print(f"{'total':63} {sum(totals.values()):7.2f}")
    if any(label == "general-purpose" for label, _m in totals):
        print(
            "\nNote: general-purpose agents usually mean a skill named an agent that does not exist (use rnd:<name>)."
        )


if __name__ == "__main__":
    main()
