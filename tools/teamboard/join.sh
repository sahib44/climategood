#!/bin/sh
# Connect this checkout's Claude to the team board.
#   sh tools/teamboard/join.sh <board-url> <token> <your-name>
# Writes .claude/settings.local.json (gitignored) and .mcp.json is already in the repo.
set -e
URL="${1%/}"; TOKEN="$2"; NAME="$3"
if [ -z "$URL" ] || [ -z "$TOKEN" ] || [ -z "$NAME" ]; then
  echo "usage: sh tools/teamboard/join.sh <board-url> <token> <your-name>"; exit 1
fi
cd "$(git rev-parse --show-toplevel)"
mkdir -p .claude
cat > .claude/settings.local.json <<EOF
{
  "env": {
    "TEAMBOARD_URL": "$URL",
    "TEAMBOARD_TOKEN": "$TOKEN",
    "TEAMBOARD_USER": "$NAME"
  },
  "enabledMcpjsonServers": ["teamboard"]
}
EOF
echo "Wrote .claude/settings.local.json for $NAME."
if curl -sf -m 5 "$URL/health" >/dev/null; then echo "Board is reachable."; else echo "WARNING: $URL/health did not answer."; fi
echo "Restart Claude in this folder, then ask it: 'check the teamboard inbox'."
