#!/usr/bin/env bash
# Auto-rebuild graphify knowledge graph on file changes.
# PostToolUse hook for Write, Edit, and Bash tools.
# Rate-limited to once per 30 seconds. Runs rebuild in background.

set -euo pipefail

LOCKFILE="/tmp/.graphify-rebuild-ts"
RATE_LIMIT=30  # seconds

# Rate limiting — check if we rebuilt recently
if [ -f "$LOCKFILE" ]; then
  LAST=$(cat "$LOCKFILE" 2>/dev/null || echo 0)
  NOW=$(date +%s)
  ELAPSED=$(( NOW - LAST ))
  [ "$ELAPSED" -lt "$RATE_LIMIT" ] && exit 0
fi

# Read hook input from stdin
INPUT=$(cat)

# Determine if this is a relevant trigger
TOOL_NAME=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('tool_name', ''))
" 2>/dev/null || true)

# For Bash: only trigger on git commit commands
if [ "$TOOL_NAME" = "Bash" ]; then
  COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('command', ''))
" 2>/dev/null || true)
  # Skip if not a git commit
  echo "$COMMAND" | grep -q 'git commit' || exit 0
fi

# For Write/Edit: extract file_path to verify it's a code/doc file
if [ "$TOOL_NAME" = "Write" ] || [ "$TOOL_NAME" = "Edit" ]; then
  FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('file_path', ''))
" 2>/dev/null || true)
  # Skip non-code/doc files (e.g., .json config, .lock, images)
  case "$FILE_PATH" in
    *.ts|*.tsx|*.js|*.jsx|*.py|*.go|*.rs|*.java|*.md|*.txt|*.rst|*.css|*.html) ;;
    *) exit 0 ;;
  esac
fi

# Walk up from CWD to find graphify-out/
GRAPH_DIR=""
DIR="$(pwd)"
while [ "$DIR" != "/" ]; do
  if [ -d "$DIR/graphify-out" ]; then
    GRAPH_DIR="$DIR"
    break
  fi
  DIR=$(dirname "$DIR")
done

# No graphify-out → skip
[ -z "$GRAPH_DIR" ] && exit 0

# Write timestamp for rate limiting
date +%s > "$LOCKFILE"

# Run incremental rebuild in background (non-blocking)
# Use pipx graphify venv Python (graphify is installed via pipx, not system Python)
GRAPHIFY_PYTHON="$HOME/.local/pipx/venvs/graphifyy/bin/python"
[ ! -f "$GRAPHIFY_PYTHON" ] && GRAPHIFY_PYTHON="python3"  # fallback

(
  cd "$GRAPH_DIR"
  "$GRAPHIFY_PYTHON" -c "
from graphify.watch import _rebuild_code
from pathlib import Path
_rebuild_code(Path('.'))
" > /tmp/.graphify-rebuild.log 2>&1
) &

exit 0
