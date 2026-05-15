#!/usr/bin/env bash
# init.sh — mechanical workspace setup.
#
# Runs every idempotent step from init-steps.sh in order, then writes the manifest.
# All steps are probe-and-apply: re-running is safe and skips work already in place.
#
# Usage:
#   init.sh <workdir> <provider> <name> <email>
#
# - <workdir>:  absolute path to the workspace root
# - <provider>: "github" or "gitlab"
# - <name>:     git user.name for this workspace
# - <email>:    git user.email for this workspace
#
# Steps the CALLER (init.md) handles, NOT this script:
#   - Step 1: prerequisite checks   (call: source lib/init-steps.sh; step_verify_prereqs)
#   - Step 2: provider auth         (interactive — gh/glab auth login)
#   - Step 7: knowledge vault init  (interactive — /knowledge-base init skill call)
#   - Step 11: optional graph build (interactive — confirm + graphify . --update)

set -uo pipefail

if [ $# -ne 4 ]; then
  echo "Usage: $0 <workdir> <provider> <name> <email>" >&2
  exit 2
fi

WORKDIR="$1"
PROVIDER="$2"
NAME="$3"
EMAIL="$4"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/init-steps.sh"

VERSION=$(awk '/^version:/{print $2; exit}' ~/.claude/skills/workdir/SKILL.md)

echo "Initializing $WORKDIR (skill v$VERSION)"
echo ""

step_gitconfig         "$WORKDIR" "$PROVIDER" "$NAME" "$EMAIL"
step_ignores           "$WORKDIR"
step_graphify_hook     "$WORKDIR"
step_coding_standards  "$WORKDIR"
step_render_claude_md  "$WORKDIR" "$PROVIDER" "$NAME" "$EMAIL"
step_claude_mem_worker
step_uipro             "$WORKDIR"
step_memory_seeds      "$WORKDIR"

bash "$SCRIPT_DIR/lib/write-manifest.sh" "$WORKDIR" "$VERSION"

echo ""
echo "Workspace initialized: $WORKDIR (skill v$VERSION)"
