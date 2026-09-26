# Contributing

Thanks for helping improve RnD. Start with [docs/DEVELOPING.md](docs/DEVELOPING.md) —
it covers set-up, the codebase rules and how to add file types, tools, commands and agents.

Before opening a pull request:

1. `make lint` and `make test` pass.
2. New behaviour has tests; changes to extraction, anchors or the verifier have tests
   against the KESTREL demo.
3. If you changed a skill, agent or tool description, run the smoke evals (`make eval`)
   and check `claude --plugin-dir plugins/rnd plugin details rnd` for the always-on token
   cost.
4. User-visible changes are listed in CHANGELOG.md.

Keep the two design promises intact: the engine is deterministic and model-free, and
nothing RnD writes for a user reaches an Office file without passing the verifier.
