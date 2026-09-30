#!/bin/bash
# Saves your Concept2 logbook API token into the Claude desktop config on this Mac
# (env C2_TOKEN for the 'rowing' MCP server) and refreshes the server file.
# The token is read from the keyboard without echo; it never touches the repo.
set -euo pipefail
UV="$HOME/.local/bin/uv"
CFG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"

curl -fsSL https://raw.githubusercontent.com/itsmefrances/rowing-plan/925f7c31942f0759a499a022586a14ab8d3304db/mcp/rowing_mcp.py \
  -o "$HOME/rowing-mcp/rowing_mcp.py"

printf "Paste your Concept2 token, then press Return (nothing will show): "
read -rs C2_TOKEN < /dev/tty
echo
[ -n "$C2_TOKEN" ] || { echo "No token entered; nothing changed."; exit 1; }

# check it against the API before saving
code=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $C2_TOKEN" \
  -H "Accept: application/vnd.c2logbook.v1+json" https://log.concept2.com/api/users/me)
if [ "$code" != "200" ]; then echo "Concept2 rejected the token (HTTP $code); nothing saved."; exit 1; fi

cp "$CFG" "$CFG.bak"
C2_TOKEN="$C2_TOKEN" "$UV" run --quiet --python 3.12 python - "$CFG" <<'PY'
import json, os, sys
cfg = sys.argv[1]
d = json.load(open(cfg))
d["mcpServers"]["rowing"].setdefault("env", {})["C2_TOKEN"] = os.environ["C2_TOKEN"]
json.dump(d, open(cfg, "w"), indent=2)
PY
chmod 600 "$CFG"
echo "Token verified and saved. Quit Claude completely (Cmd-Q) and reopen it."
