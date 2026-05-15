#!/usr/bin/env bash
# clone.sh — mechanical portion of /workdir clone.
#
# Handles URL normalisation (host/SSH-port detection from existing repos), the actual git
# clone, scaffolding test-cases/README.md (static template), inserting the @include line
# into the workspace CLAUDE.md, and rebuilding the cross-repo graphify graph.
#
# NOT handled here (stays in commands/clone.md — needs LLM):
#   - Confirming the auto-detected group with the user (AskUserQuestion)
#   - Generating Features.md content from a fresh repo scan (semantic LLM work)
#   - Offering the per-repo graphify hook (AskUserQuestion)
#
# Usage:
#   clone.sh <repo-arg> [<manual-group>]
#
# - <repo-arg>:     URL or `owner/repo` shorthand
# - <manual-group>: optional override; empty/unset auto-detects from the URL
#
# Outputs key/value lines on stdout that the caller (clone.md) can parse:
#   WORKDIR=<path>
#   PROVIDER=<github|gitlab>
#   REPO_URL=<resolved-url>
#   REPO_NAME=<basename without .git>
#   GROUP=<group path>
#   REPO_PATH=<workdir>/<group>/<repo-name>
#   CLONE_OK=true|false
#   FEATURES_NEW=true|false
#   TESTCASES_NEW=true|false
#   INCLUDE_STATUS=added|placeholder|exists|no-projects-section
#   GRAPH_REBUILD=ok|fail|noop

set -uo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <repo-arg> [<manual-group>]" >&2
  exit 2
fi

REPO_ARG="$1"
MANUAL_GROUP="${2:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/find-workdir.sh"
echo "WORKDIR=$WORKDIR"

# Provider from workspace CLAUDE.md (top-of-file, not the Git Configuration footer)
PROVIDER=$(grep -m1 "^Provider:" "$WORKDIR/CLAUDE.md" 2>/dev/null | awk '{print $2}')
if [ -z "$PROVIDER" ]; then
  echo "PROVIDER="
  echo "ERROR: workspace CLAUDE.md is missing 'Provider:' line — run /workdir init first" >&2
  exit 1
fi
echo "PROVIDER=$PROVIDER"

# ------------------------------------------------------------------------------
# Normalize repo identifier — detect host/SSH-port from any existing repo's origin
# ------------------------------------------------------------------------------
REPO_URL=""
if echo "$REPO_ARG" | grep -qE '^(https?://|git@|ssh://)'; then
  REPO_URL="$REPO_ARG"
else
  # owner/repo shorthand — expand using existing workspace patterns
  DETECTED_REMOTE=$(find "$WORKDIR" -mindepth 3 -maxdepth 4 -type d -name ".git" -print 2>/dev/null \
    | head -1 \
    | xargs -I{} dirname {} 2>/dev/null \
    | xargs -I{} git -C {} remote get-url origin 2>/dev/null \
    | head -1)

  case "$PROVIDER" in
    github)
      if echo "$DETECTED_REMOTE" | grep -q "@"; then
        HOST=$(echo "$DETECTED_REMOTE" | sed -E 's|.*@([^:/]+).*|\1|')
        REPO_URL="git@${HOST}:${REPO_ARG}.git"
      else
        HOST=$(echo "$DETECTED_REMOTE" | sed -E 's|https?://([^/]+).*|\1|')
        HOST=${HOST:-github.com}
        REPO_URL="https://${HOST}/${REPO_ARG}.git"
      fi
      ;;
    gitlab)
      if echo "$DETECTED_REMOTE" | grep -qE '^ssh://'; then
        HOST_PORT=$(echo "$DETECTED_REMOTE" | sed -E 's|ssh://[^@]+@([^/]+)/.*|\1|')
        REPO_URL="ssh://git@${HOST_PORT}/${REPO_ARG}.git"
      elif echo "$DETECTED_REMOTE" | grep -q "@"; then
        HOST=$(echo "$DETECTED_REMOTE" | sed -E 's|.*@([^:/]+).*|\1|')
        REPO_URL="git@${HOST}:${REPO_ARG}.git"
      else
        HOST=$(echo "$DETECTED_REMOTE" | sed -E 's|https?://([^/]+).*|\1|')
        HOST=${HOST:-gitlab.com}
        REPO_URL="https://${HOST}/${REPO_ARG}.git"
      fi
      ;;
  esac
fi

REPO_NAME=$(basename "$REPO_URL" .git)
echo "REPO_URL=$REPO_URL"
echo "REPO_NAME=$REPO_NAME"

# ------------------------------------------------------------------------------
# Determine group
# ------------------------------------------------------------------------------
GROUP=""
if [ -n "$MANUAL_GROUP" ]; then
  GROUP="$MANUAL_GROUP"
else
  # Auto-detect from URL path
  # Strip the trailing repo name to get the namespace
  PATH_PART=$(echo "$REPO_URL" | sed -E -e 's|^https?://[^/]+/||' -e 's|^git@[^:]+:||' -e 's|^ssh://[^/]+/||' -e 's|\.git$||')
  GROUP=$(dirname "$PATH_PART")
  [ "$GROUP" = "." ] && GROUP="$REPO_NAME"   # degenerate fallback (no namespace in URL)
fi
echo "GROUP=$GROUP"

REPO_PATH="$WORKDIR/$GROUP/$REPO_NAME"
echo "REPO_PATH=$REPO_PATH"

# ------------------------------------------------------------------------------
# Clone (CLI preferred, plain git fallback)
# ------------------------------------------------------------------------------
mkdir -p "$WORKDIR/$GROUP"
CLONE_OK=false

if [ -d "$REPO_PATH/.git" ]; then
  echo "✓ Already cloned at $REPO_PATH (skipping clone)"
  CLONE_OK=true
else
  # Owner/repo shorthand for the provider CLI
  OWNER_REPO=$(echo "$REPO_URL" | sed -E -e 's|^https?://[^/]+/||' -e 's|^git@[^:]+:||' -e 's|^ssh://[^/]+/||' -e 's|\.git$||')

  case "$PROVIDER" in
    github)
      if gh repo clone "$OWNER_REPO" "$REPO_PATH" 2>&1; then
        CLONE_OK=true
      fi ;;
    gitlab)
      if glab repo clone "$OWNER_REPO" "$REPO_PATH" 2>&1; then
        CLONE_OK=true
      fi ;;
  esac

  # Fallback: plain git
  if [ "$CLONE_OK" = false ]; then
    echo "+ CLI clone failed, falling back to plain git"
    if git clone "$REPO_URL" "$REPO_PATH" 2>&1; then
      CLONE_OK=true
    fi
  fi
fi

echo "CLONE_OK=$CLONE_OK"
if [ "$CLONE_OK" = false ]; then
  echo "ERROR: clone failed for $REPO_URL — see above" >&2
  exit 1
fi

# ------------------------------------------------------------------------------
# Scaffold test-cases/ (static template) — Features.md is left for the LLM to generate
# ------------------------------------------------------------------------------
TESTCASES_NEW=false
if [ ! -d "$REPO_PATH/test-cases" ]; then
  mkdir -p "$REPO_PATH/test-cases"
  TESTCASES_TEMPLATE="$SCRIPT_DIR/../templates/test-cases-README.md"
  if [ -f "$TESTCASES_TEMPLATE" ]; then
    cp "$TESTCASES_TEMPLATE" "$REPO_PATH/test-cases/README.md"
  else
    echo "⚠ test-cases template missing at $TESTCASES_TEMPLATE — created empty dir"
  fi
  TESTCASES_NEW=true
fi
echo "TESTCASES_NEW=$TESTCASES_NEW"

FEATURES_NEW=false
[ ! -f "$REPO_PATH/Features.md" ] && FEATURES_NEW=true
echo "FEATURES_NEW=$FEATURES_NEW"

# ------------------------------------------------------------------------------
# Insert @include line into workspace CLAUDE.md (idempotent)
# ------------------------------------------------------------------------------
INCLUDE_LINE="@$GROUP/$REPO_NAME/CLAUDE.md"
INCLUDE_STATUS=""

if grep -qF "$INCLUDE_LINE" "$WORKDIR/CLAUDE.md" 2>/dev/null; then
  INCLUDE_STATUS="exists"
else
  if grep -q '^## Projects' "$WORKDIR/CLAUDE.md" 2>/dev/null; then
    # Insert just after the last existing @include in the Projects section, or right after
    # the placeholder comment if none.
    if [ -f "$REPO_PATH/CLAUDE.md" ]; then
      NEW_ENTRY="$INCLUDE_LINE"
      INCLUDE_STATUS="added"
    else
      NEW_ENTRY="<!-- $GROUP/$REPO_NAME — no CLAUDE.md (add one and re-run /workdir clone to activate) -->"
      INCLUDE_STATUS="placeholder"
    fi

    awk -v new="$NEW_ENTRY" '
      /^## Projects[[:space:]]*$/ { print; in_section=1; next }
      in_section && /^## /         { print new; print ""; in_section=0 }
      { print }
      END { if (in_section) { print new; print "" } }
    ' "$WORKDIR/CLAUDE.md" > "$WORKDIR/CLAUDE.md.tmp" && mv "$WORKDIR/CLAUDE.md.tmp" "$WORKDIR/CLAUDE.md"
  else
    INCLUDE_STATUS="no-projects-section"
  fi
fi
echo "INCLUDE_STATUS=$INCLUDE_STATUS"

# ------------------------------------------------------------------------------
# Rebuild cross-repo graphify graph
# ------------------------------------------------------------------------------
GRAPH_REBUILD="noop"
if command -v graphify >/dev/null 2>&1; then
  if (cd "$WORKDIR" && graphify update . >/dev/null 2>&1); then
    GRAPH_REBUILD="ok"
  else
    GRAPH_REBUILD="fail"
  fi
fi
echo "GRAPH_REBUILD=$GRAPH_REBUILD"

echo ""
echo "✓ Clone complete: $GROUP/$REPO_NAME at $REPO_PATH"
