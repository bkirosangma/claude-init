#!/usr/bin/env bash
# crystallize.sh — SessionEnd hook for Tier 2→3 promotion
# Finds observation clusters with ≥5 entries on shared concepts,
# distills them into structured knowledge pages.

set -euo pipefail

DB="$HOME/.claude-mem/claude-mem.db"
[ -f "$DB" ] || exit 0

CRYSTAL_DIR="$HOME/.claude-mem/crystallized"
mkdir -p "$CRYSTAL_DIR"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/crystallize_impl.py" 2>/dev/null || true
