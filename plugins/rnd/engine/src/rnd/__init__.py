"""RnD engine: deterministic, model-free document plumbing for Claude Code.

Everything in this package is exact and reproducible. Intelligence (query expansion,
summarising, reasoning) lives in the Claude Code agents that call these tools; the
engine only extracts, indexes, computes and verifies.
"""

__version__ = "0.1.0"
