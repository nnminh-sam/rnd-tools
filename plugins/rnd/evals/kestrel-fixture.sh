#!/bin/sh
# Seeds an eval run's empty workspace with the KESTREL demo and indexes it.
# Called by each case's fixture.sh; runs outside the agent sandbox (needs --scaffold).
set -eu
PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[ -d "$PLUGIN_ROOT/demo/kestrel-chair" ] || { echo "demo not found under $PLUGIN_ROOT" >&2; exit 1; }
cp -R "$PLUGIN_ROOT/demo/kestrel-chair/." .
uv run --quiet --frozen --project "$PLUGIN_ROOT/engine" rnd init . --name KESTREL > /dev/null
