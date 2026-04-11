#!/usr/bin/env bash
# contradiction-check.sh — PostToolUse hook for conflict detection
# Rate-limited to run at most once every 30 seconds.
# Delegates to contradiction_check.py for the actual logic.

set -euo pipefail

DB="$HOME/.claude-mem/claude-mem.db"
[ -f "$DB" ] || exit 0

LOCKFILE="/tmp/hybrid-search-contradiction.lock"

# Rate limit: skip if ran within last 30 seconds
if [ -f "$LOCKFILE" ]; then
  LAST_RUN=$(cat "$LOCKFILE" 2>/dev/null || echo 0)
  NOW=$(date +%s)
  ELAPSED=$((NOW - LAST_RUN))
  [ "$ELAPSED" -lt 30 ] && exit 0
fi

# Update lockfile
date +%s > "$LOCKFILE"

# Run the Python contradiction checker
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/contradiction_check.py" 2>/dev/null || true
