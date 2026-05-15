#!/usr/bin/env bash
# changelog-diff.sh — print the CHANGELOG sections newer than a given prior version.
#
# Usage:
#   changelog-diff.sh <prior-version>
#
# Reads `~/.claude/skills/workdir/CHANGELOG.md` and prints every `## <ver> — <date>` section
# from the top until it hits one that matches `<prior-version>`. Output is the literal
# changelog markdown ready to show the user.
#
# Prints nothing (exit 0) if prior-version is empty, "legacy", or matches the current.

set -uo pipefail

PRIOR="${1:-}"
CHANGELOG=~/.claude/skills/workdir/CHANGELOG.md

if [ -z "$PRIOR" ] || [ "$PRIOR" = "legacy" ]; then
  exit 0
fi

if [ ! -f "$CHANGELOG" ]; then
  echo "ERROR: changelog not found at $CHANGELOG" >&2
  exit 1
fi

awk -v prior="$PRIOR" '
  /^## / && $2 == prior { exit }
  /^## / { active=1 }
  active { print }
' "$CHANGELOG"
