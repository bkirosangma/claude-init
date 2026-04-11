#!/usr/bin/env bash
# bump-relevance.sh — PostToolUse hook on get_observations
# Increments relevance_count for fetched observations, extending their decay half-life.
# Observations that are frequently accessed decay slower (they remain relevant).

set -euo pipefail

DB="$HOME/.claude-mem/claude-mem.db"
[ -f "$DB" ] || exit 0

# Read hook input from stdin
INPUT=$(cat)

# Extract the observation IDs from the tool input
# get_observations accepts { ids: [1, 2, 3] }
IDS=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    ids = data.get('tool_input', {}).get('ids', [])
    if ids:
        print(','.join(str(int(i)) for i in ids))
except:
    pass
" 2>/dev/null || true)

[ -z "$IDS" ] && exit 0

# Increment relevance_count for all fetched observations
# Skip crystallized ones (relevance_count == -1)
sqlite3 "$DB" "UPDATE observations SET relevance_count = relevance_count + 1 WHERE id IN ($IDS) AND relevance_count >= 0;" 2>/dev/null || true
