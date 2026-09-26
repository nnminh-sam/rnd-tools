ENGINE := plugins/rnd/engine
UV := uv run --project $(ENGINE)

.PHONY: sync test lint format demo validate details eval eval-all

sync:        ## install engine dependencies
	uv sync --project $(ENGINE)

test:        ## engine unit + integration tests (no model calls)
	cd $(ENGINE) && uv run pytest -q

lint:        ## ruff lint + format check
	cd $(ENGINE) && uv run ruff check src tests tools && uv run ruff format --check src tests tools

format:
	cd $(ENGINE) && uv run ruff format src tests tools && uv run ruff check --fix src tests tools

demo:        ## regenerate demo workspace, TUTORIAL.md and golden facts
	cd $(ENGINE) && uv run python tools/build_demo.py

validate:    ## validate plugin, marketplace, skills and agents
	claude plugin validate plugins/rnd && claude plugin validate . \
	  && claude plugin validate plugins/rnd/skills && claude plugin validate plugins/rnd/agents

details:     ## component inventory and always-on token cost
	claude --plugin-dir plugins/rnd plugin details rnd

eval:        ## model-backed smoke evals (costs tokens)
	claude plugin eval plugins/rnd --scaffold --mocks off --allow-tools 'mcp__plugin_rnd_rnd__*' Write Edit Agent Skill --runs 1 --tag smoke --max-cost-usd 5

eval-all:    ## all evals incl. decide/report (costs more tokens)
	claude plugin eval plugins/rnd --scaffold --mocks off --allow-tools 'mcp__plugin_rnd_rnd__*' Write Edit Agent Skill --runs 1 --max-cost-usd 20
