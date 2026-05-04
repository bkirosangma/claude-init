#!/usr/bin/env bash
# SessionStart hook — silently warn if newer commits exist on the configured
# marketplace ref. All plugins from the same marketplace share a 1-hour
# timestamp cache so only one hook hits the network per session — the rest
# exit immediately and read the same cached state.
#
# Token cost: zero unless drift is detected; the script source is never
# loaded into Claude's context (only its stdout is consumed).
#
# This file is the canonical update-check hook for the marketplace. It is
# reused unchanged across every plugin (plugin and marketplace names are
# derived from CLAUDE_PLUGIN_ROOT, not hardcoded).

set -u

plugin_root="${CLAUDE_PLUGIN_ROOT:-}"
[ -n "$plugin_root" ] || exit 0

# Derive plugin and marketplace names from the install layout:
#   ~/.claude/plugins/marketplaces/<marketplace>/plugins/<plugin>/
plugin_name=$(basename "$plugin_root")
marketplace_name=$(basename "$(dirname "$(dirname "$plugin_root")")")

# Shared cache across all plugins from this marketplace
CACHE_DIR="$HOME/.config/$marketplace_name"
CACHE_FILE="$CACHE_DIR/.last_update_check"
CACHE_TTL=3600  # 1 hour

NOW=$(date +%s)
LAST=$(cat "$CACHE_FILE" 2>/dev/null || echo 0)
if [ $((NOW - LAST)) -lt "$CACHE_TTL" ]; then
    exit 0  # Recently checked by another plugin's hook (or this one) — skip
fi

# The plugin lives N levels deep inside the marketplace clone — find the
# enclosing .git automatically rather than hard-coding `../..`.
mp_root=$(git -C "$plugin_root" rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -d "$mp_root/.git" ] || exit 0

# Stay silent on detached HEAD (some Claude Code installs check out by SHA).
branch=$(git -C "$mp_root" symbolic-ref --short HEAD 2>/dev/null) || exit 0
[ -n "$branch" ] || exit 0

local_sha=$(git -C "$mp_root" rev-parse HEAD 2>/dev/null) || exit 0

# `ls-remote` reuses whatever auth the marketplace clone already has
# (macOS keychain, SSH agent, token-in-URL). Failure → empty → silent exit
# WITHOUT updating the cache (so the next hook will retry).
remote_sha=$(git -C "$mp_root" ls-remote origin "$branch" 2>/dev/null | awk 'NR==1 {print $1}')
[ -n "$remote_sha" ] || exit 0

# Network check completed — record timestamp regardless of drift outcome
mkdir -p "$CACHE_DIR" 2>/dev/null
echo "$NOW" > "$CACHE_FILE"

[ "$local_sha" = "$remote_sha" ] && exit 0

# Drift detected. Emit a single-line systemMessage so Claude sees it AND it
# surfaces to the user in the terminal. Both SHAs are 40-hex; safe to inline
# without JSON-escaping.
short_local="${local_sha:0:7}"
short_remote="${remote_sha:0:7}"
printf '{"continue": true, "systemMessage": "%s plugin update available (%s -> %s on %s). Run: claude plugin update %s@%s, then restart claude to pick it up."}\n' \
  "$plugin_name" "$short_local" "$short_remote" "$branch" "$plugin_name" "$marketplace_name"
exit 0
