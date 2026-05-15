#!/usr/bin/env bash
# update.sh — bring an existing workspace up to the current skill version.
#
# Runs the upgrade-relevant subset of init steps from init-steps.sh. Skips:
#   - Prerequisite checks (workspace existed → prereqs were met)
#   - Provider auth (preserved by provider CLI)
#   - Gitconfig (identity rarely changes; re-run /workdir init to update)
#   - Optional initial graph build (auto-rebuild hook keeps the graph fresh)
#
# Usage:
#   update.sh           # locate workdir via find-workdir, refuse if no marker
#
# Sets manifest to the current skill version on completion. Refuses if there's no existing
# workspace at the resolved workdir.

set -uo pipefail

# Parse args
PLAN_ONLY=false
[ "${1:-}" = "--plan" ] && PLAN_ONLY=true

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Locate workspace (hard refusal mode — update requires an existing workspace)
source "$SCRIPT_DIR/lib/find-workdir.sh"
source "$SCRIPT_DIR/lib/init-steps.sh"

VERSION=$(awk '/^version:/{print $2; exit}' ~/.claude/skills/workdir/SKILL.md)

# Detect prior state (sets PRIOR_VERSION, PRIOR_AT, STATE)
step_detect_prior "$WORKDIR"

if [ "$STATE" = "NEW" ]; then
  echo "ERROR: no workdir workspace found at $WORKDIR" >&2
  echo "       Run /workdir init <github|gitlab> first." >&2
  exit 1
fi

echo "Workspace:        $WORKDIR"
echo "Last init:        ${PRIOR_VERSION:-legacy} ${PRIOR_AT:+at $PRIOR_AT}"
echo "Current skill:    $VERSION"
echo ""

# Print changelog diff if upgrading
bash "$SCRIPT_DIR/lib/changelog-diff.sh" "$PRIOR_VERSION"

if [ "$PLAN_ONLY" = true ]; then
  echo ""
  echo "Plan only — re-run without --plan to apply."
  exit 0
fi

echo ""
echo "Running idempotent steps..."

# Run the upgrade subset (skip step_gitconfig and step_verify_prereqs)
step_ignores           "$WORKDIR"
step_graphify_hook     "$WORKDIR"
step_coding_standards  "$WORKDIR"
# Re-rendering CLAUDE.md requires provider/name/email — read them from existing config
EXISTING_PROVIDER=$(grep -m1 "^Provider:" "$WORKDIR/CLAUDE.md" 2>/dev/null | awk '{print $2}')
EXISTING_NAME=$(git config -f "$WORKDIR/.gitconfig" --get user.name 2>/dev/null || echo "")
EXISTING_EMAIL=$(git config -f "$WORKDIR/.gitconfig" --get user.email 2>/dev/null || echo "")
if [ -n "$EXISTING_PROVIDER" ] && [ -n "$EXISTING_NAME" ] && [ -n "$EXISTING_EMAIL" ]; then
  step_render_claude_md "$WORKDIR" "$EXISTING_PROVIDER" "$EXISTING_NAME" "$EXISTING_EMAIL"
else
  echo "⚠ CLAUDE.md: cannot refresh — provider/name/email missing from workspace config"
fi
step_claude_mem_worker
step_uipro             "$WORKDIR"
step_memory_seeds      "$WORKDIR"

# Persist updated manifest
bash "$SCRIPT_DIR/lib/write-manifest.sh" "$WORKDIR" "$VERSION"

echo ""
echo "Workspace updated: $WORKDIR"
echo ""
echo "  Skill version:   ${PRIOR_VERSION:-legacy} → $VERSION"
echo "  Manifest:        $WORKDIR/.workdir/state.json"
echo ""
echo "Next:"
echo "  Re-run anytime:  /workdir update"
echo "  Full re-init:    /workdir init <github|gitlab>"
echo "  Clone a repo:    /workdir clone <url>"
echo "  Pull all repos:  /workdir pull"
