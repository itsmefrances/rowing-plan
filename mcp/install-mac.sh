#!/bin/bash
# Installs the rowing MCP server (Concept2 tools) on this Mac for the Claude desktop app.
# No tokens are set: Concept2 is public, HubFit/ErgZone stay off.
set -euo pipefail

# 1. uv (brings its own Python; no Xcode tools needed)
if [ ! -x "$HOME/.local/bin/uv" ]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
UV="$HOME/.local/bin/uv"

# 2. the server file, straight from the repo
mkdir -p "$HOME/rowing-mcp"
curl -fsSL https://raw.githubusercontent.com/itsmefrances/rowing-plan/main/mcp/rowing_mcp.py \
  -o "$HOME/rowing-mcp/rowing_mcp.py"

# 3. pre-warm the dependencies so the first start is quick
"$UV" run --quiet --with "mcp[cli]" --with certifi python -c "import mcp, certifi; print('deps ok')"

# 4. register it with the Claude desktop app (keeps anything already there; backs up first)
CFG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
mkdir -p "$(dirname "$CFG")"
[ -f "$CFG" ] && cp "$CFG" "$CFG.bak"
"$UV" run --quiet python - "$CFG" "$HOME" <<'PY'
import json, os, sys
cfg, home = sys.argv[1], sys.argv[2]
d = json.load(open(cfg)) if os.path.exists(cfg) and os.path.getsize(cfg) else {}
d.setdefault("mcpServers", {})["rowing"] = {
    "command": f"{home}/.local/bin/uv",
    "args": ["run", "--quiet", "--with", "mcp[cli]", "--with", "certifi",
             f"{home}/rowing-mcp/rowing_mcp.py"],
    "env": {"C2_PROFILE": "2198296"},
}
json.dump(d, open(cfg, "w"), indent=2)
print("registered 'rowing' in", cfg)
PY

echo "Done. Quit Claude completely (Cmd-Q) and reopen it."
