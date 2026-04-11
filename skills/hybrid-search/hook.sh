#!/usr/bin/env bash
# hybrid-search auto-trigger hook
# Enriches Read operations with graphify graph context + MEMORY.md entries
# Runs as a PreToolUse hook on "Read"
# Features: session dedup (skip re-enriched files), token budget (taper at 50KB, stop at 100KB)

set -euo pipefail

# Read hook input from stdin
INPUT=$(cat)

# Extract the file_path from tool_input
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('file_path', ''))
" 2>/dev/null || true)

# No file path → nothing to do
[ -z "$FILE_PATH" ] && exit 0

# ── Session dedup + token budget ──
SESSION_FILE="/tmp/.hybrid-search-session-$$"
# Parent PID for shared session across tool calls
PPID_SESSION="/tmp/.hybrid-search-session-$PPID"
# Use PPID if available (subprocesses share parent), fall back to $$
[ -f "$PPID_SESSION" ] && SESSION_FILE="$PPID_SESSION"

# Clean stale session files (>2 hours old)
find /tmp -maxdepth 1 -name '.hybrid-search-session-*' -mmin +120 -delete 2>/dev/null || true

# Check if this file was already enriched
if [ -f "$SESSION_FILE" ]; then
  if grep -qF "$FILE_PATH" "$SESSION_FILE" 2>/dev/null; then
    exit 0  # Already enriched, skip
  fi
  # Check token budget (bytes as proxy for tokens)
  BUDGET_USED=$(head -1 "$SESSION_FILE" 2>/dev/null | grep -o '^BYTES:[0-9]*' | cut -d: -f2 || echo 0)
  [ -z "$BUDGET_USED" ] && BUDGET_USED=0
  # >100KB total injection → stop entirely
  [ "$BUDGET_USED" -gt 102400 ] && exit 0
fi

# Find graphify-out/graph.json relative to the project
# Walk up from CWD looking for graphify-out/graph.json
GRAPH_FILE=""
DIR="$(pwd)"
while [ "$DIR" != "/" ]; do
  if [ -f "$DIR/graphify-out/graph.json" ]; then
    GRAPH_FILE="$DIR/graphify-out/graph.json"
    break
  fi
  DIR=$(dirname "$DIR")
done

# No graph → skip silently
[ -z "$GRAPH_FILE" ] && exit 0

# Check file size (bytes)
if [[ "$OSTYPE" == darwin* ]]; then
  GRAPH_SIZE=$(stat -f%z "$GRAPH_FILE" 2>/dev/null || echo 0)
else
  GRAPH_SIZE=$(stat -c%s "$GRAPH_FILE" 2>/dev/null || echo 0)
fi

# Only do direct read for graphs <=500KB
# For larger graphs, skip auto-trigger (user should use /hybrid-search manually or start MCP)
[ "$GRAPH_SIZE" -gt 512000 ] && exit 0

# Extract the basename of the file being read (for node matching)
BASENAME=$(basename "$FILE_PATH")

# Use Python to find the node and its neighbors in the graph
CONTEXT=$(python3 -c "
import json, sys

try:
    with open('$GRAPH_FILE') as f:
        g = json.load(f)
except:
    sys.exit(0)

nodes = {n['id']: n for n in g.get('nodes', [])}
links = g.get('links', [])

# Find node matching the file being read
basename = '$BASENAME'.lower()
file_path = '$FILE_PATH'.lower()
match = None
for nid, n in nodes.items():
    label = n.get('label', '').lower()
    src = n.get('source_file', '').lower()
    if basename in label or basename in src or file_path.endswith(src):
        match = nid
        break

if not match:
    sys.exit(0)

node = nodes[match]
community = node.get('community', '?')

# Find neighbors (1 hop)
neighbors = []
for link in links:
    src, tgt = link.get('source', ''), link.get('target', '')
    rel = link.get('relation', 'related_to')
    conf = link.get('confidence', 'EXTRACTED')
    if src == match and tgt in nodes:
        neighbors.append(f'  -> {nodes[tgt].get(\"label\", tgt)} [{rel}] ({conf})')
    elif tgt == match and src in nodes:
        neighbors.append(f'  <- {nodes[src].get(\"label\", src)} [{rel}] ({conf})')

if not neighbors:
    sys.exit(0)

# Cap at 8 neighbors to keep context compact
neighbors = neighbors[:8]
extra = ''
total = sum(1 for l in links if l.get('source') == match or l.get('target') == match)
if total > 8:
    extra = f'\n  ... and {total - 8} more connections'

print(f'GRAPH CONTEXT for {node.get(\"label\", basename)} (community {community}):')
print('\n'.join(neighbors) + extra)
" 2>/dev/null || true)

# ── MEMORY.md scanning ──
# Dynamic path: /Users/kiro/foo → -Users-kiro-foo
MEMORY_DIR="$HOME/.claude/projects/$(echo "$PWD" | sed 's|^/|-|; s|/|-|g')/memory"
MEMORY_CONTEXT=""
if [ -d "$MEMORY_DIR" ]; then
  MEMORY_CONTEXT=$(python3 -c "
import os, sys

memory_dir = '$MEMORY_DIR'
basename = '${BASENAME}'.lower().replace('.tsx','').replace('.ts','').replace('.js','').replace('.py','')
results = []

for f in os.listdir(memory_dir):
    if f == 'MEMORY.md' or not f.endswith('.md'):
        continue
    path = os.path.join(memory_dir, f)
    try:
        with open(path) as fh:
            content = fh.read()
    except:
        continue
    if basename in content.lower():
        for line in content.split('\n'):
            if line.startswith('name:'):
                results.append(line.split(':', 1)[1].strip())
                break

if results:
    print('MEMORY: ' + '; '.join(results))
" 2>/dev/null || true)
fi

# Combine graph context + memory context
FULL_CONTEXT=""
[ -n "$CONTEXT" ] && FULL_CONTEXT="$CONTEXT"
if [ -n "$MEMORY_CONTEXT" ]; then
  [ -n "$FULL_CONTEXT" ] && FULL_CONTEXT="$FULL_CONTEXT
$MEMORY_CONTEXT" || FULL_CONTEXT="$MEMORY_CONTEXT"
fi

# Output as hookSpecificOutput if we found context
if [ -n "$FULL_CONTEXT" ]; then
  # Check token budget — if >50KB, strip to graph-only (skip memory)
  if [ -f "$SESSION_FILE" ]; then
    BUDGET_USED=$(head -1 "$SESSION_FILE" 2>/dev/null | grep -o '^BYTES:[0-9]*' | cut -d: -f2 || echo 0)
    [ -z "$BUDGET_USED" ] && BUDGET_USED=0
    if [ "$BUDGET_USED" -gt 51200 ] && [ -n "$CONTEXT" ]; then
      FULL_CONTEXT="$CONTEXT"  # Graph-only, drop memory
    fi
  fi

  # Escape for JSON
  ESCAPED=$(echo "$FULL_CONTEXT" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))" 2>/dev/null)
  echo "{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"additionalContext\":$ESCAPED}}"

  # Track this file + update byte counter
  CONTEXT_BYTES=${#FULL_CONTEXT}
  if [ -f "$SESSION_FILE" ]; then
    OLD_BYTES=$(head -1 "$SESSION_FILE" 2>/dev/null | grep -o '^BYTES:[0-9]*' | cut -d: -f2 || echo 0)
    [ -z "$OLD_BYTES" ] && OLD_BYTES=0
    NEW_BYTES=$(( OLD_BYTES + CONTEXT_BYTES ))
    # Rewrite first line with updated budget, keep rest
    TAIL=$(tail -n +2 "$SESSION_FILE" 2>/dev/null || true)
    echo "BYTES:$NEW_BYTES" > "$SESSION_FILE"
    [ -n "$TAIL" ] && echo "$TAIL" >> "$SESSION_FILE"
  else
    echo "BYTES:$CONTEXT_BYTES" > "$SESSION_FILE"
  fi
  echo "$FILE_PATH" >> "$SESSION_FILE"
fi
