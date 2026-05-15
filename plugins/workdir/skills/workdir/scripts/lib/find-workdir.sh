#!/usr/bin/env bash
# find-workdir.sh — walk up from $(pwd) to locate the managed workspace root.
#
# This file is meant to be SOURCED, not executed:
#     source ~/.claude/skills/workdir/scripts/lib/find-workdir.sh [--soft]
#
# After sourcing, these variables are set:
#   ORIG_PWD     — the original $(pwd) (unchanged)
#   WORKDIR      — the workspace root, or $ORIG_PWD if not found and --soft was passed
#
# Modes:
#   (default)    Hard refusal: if no `.workdir/` (or legacy `.init-workdir/`) marker is found
#                anywhere up the tree, prints an error and `exit 1`s the caller.
#   --soft       Soft fallback: if no marker found, sets WORKDIR=$ORIG_PWD silently. Use this
#                in `init` where a fresh init at the current directory is legitimate.

_find_workdir_soft=false
[ "${1:-}" = "--soft" ] && _find_workdir_soft=true

ORIG_PWD=$(pwd)
WORKDIR="$ORIG_PWD"
while [ "$WORKDIR" != "/" ] && [ ! -d "$WORKDIR/.workdir" ] && [ ! -d "$WORKDIR/.init-workdir" ]; do
  WORKDIR=$(dirname "$WORKDIR")
done

if [ "$WORKDIR" = "/" ]; then
  if [ "$_find_workdir_soft" = "true" ]; then
    WORKDIR="$ORIG_PWD"   # fresh-init fallback
  else
    echo "ERROR: no .workdir/ marker found in any parent of $ORIG_PWD" >&2
    echo "       Run /workdir init <github|gitlab> from your workspace root first," >&2
    echo "       or cd into a managed workspace before invoking this command." >&2
    exit 1
  fi
else
  [ "$WORKDIR" != "$ORIG_PWD" ] && echo "Detected workdir: $WORKDIR (invoked from $ORIG_PWD)"
fi

# Auto-migrate legacy state dir (v1 .init-workdir/ → v2 .workdir/)
if [ -d "$WORKDIR/.init-workdir" ] && [ ! -d "$WORKDIR/.workdir" ]; then
  mv "$WORKDIR/.init-workdir" "$WORKDIR/.workdir"
  echo "Migrated state dir:  .init-workdir/ → .workdir/ (v1 → v2 layout)"
fi

unset _find_workdir_soft
