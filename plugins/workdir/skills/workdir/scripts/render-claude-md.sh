#!/usr/bin/env bash
# render-claude-md.sh — render the workspace CLAUDE.md from template, preserving any
# existing `## Projects` @include lines.
#
# Usage:
#   render-claude-md.sh <workdir> <provider> <name> <email>
#
# - <workdir>:  absolute path to the workspace root
# - <provider>: "github" or "gitlab"
# - <name>:     git user.name for this workspace
# - <email>:    git user.email for this workspace
#
# If <workdir>/CLAUDE.md exists and has a `## Projects` section, every @include line
# (and surrounding comments other than the template's auto-include placeholder) is preserved.

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
TEMPLATE="$SCRIPT_DIR/../templates/workspace-CLAUDE.md.template"
TARGET="$WORKDIR/CLAUDE.md"

if [ ! -f "$TEMPLATE" ]; then
  echo "ERROR: template not found at $TEMPLATE" >&2
  exit 1
fi

case "$PROVIDER" in
  github) CLI="gh" ;;
  gitlab) CLI="glab" ;;
  *) echo "ERROR: provider must be 'github' or 'gitlab', got '$PROVIDER'" >&2; exit 2 ;;
esac

WORKDIR_BASENAME=$(basename "$WORKDIR")

# Extract preserved @include lines from existing CLAUDE.md, if any.
# Capture everything between "## Projects" and the next "## " heading, dropping the auto-
# include placeholder comment (re-inserted from the template) and any leading/trailing blank
# lines. Surviving lines are user content — typically `@<group>/<repo>/CLAUDE.md` includes.
PRESERVED_PROJECTS=""
if [ -f "$TARGET" ]; then
  PRESERVED_PROJECTS=$(awk '
    /^## Projects[[:space:]]*$/  { in_section = 1; next }
    in_section && /^## /          { in_section = 0 }
    in_section {
      if ($0 ~ /^<!-- @includes are added automatically/) next
      print
    }
  ' "$TARGET")
  # Trim leading/trailing blank lines
  PRESERVED_PROJECTS=$(printf '%s' "$PRESERVED_PROJECTS" | awk '
    NF { p = 1 }
    p  { lines[++n] = $0 }
    END {
      end = n
      while (end > 0 && lines[end] ~ /^[[:space:]]*$/) end--
      for (i = 1; i <= end; i++) print lines[i]
    }
  ')
fi

# Render: substitute placeholders via env vars (safer than shell interpolation for values
# that might contain special characters).
export WORKDIR_BASENAME WORKDIR PROVIDER CLI NAME EMAIL PRESERVED_PROJECTS
python3 - "$TEMPLATE" "$TARGET" <<'PY'
import os, sys

template_path, target_path = sys.argv[1], sys.argv[2]
with open(template_path) as fh:
    content = fh.read()

substitutions = {
    "{{WORKDIR_BASENAME}}":   os.environ.get("WORKDIR_BASENAME", ""),
    "{{WORKDIR}}":            os.environ.get("WORKDIR", ""),
    "{{PROVIDER}}":           os.environ.get("PROVIDER", ""),
    "{{CLI}}":                os.environ.get("CLI", ""),
    "{{NAME}}":               os.environ.get("NAME", ""),
    "{{EMAIL}}":              os.environ.get("EMAIL", ""),
    "{{PROJECTS_INCLUDES}}":  os.environ.get("PRESERVED_PROJECTS", ""),
}
for key, value in substitutions.items():
    content = content.replace(key, value)

# Collapse 3+ consecutive newlines to 2 — an empty PROJECTS_INCLUDES substitution can leave
# extra blank lines where the template had a placeholder.
import re
content = re.sub(r'\n{3,}', '\n\n', content)

with open(target_path, "w") as fh:
    fh.write(content)
PY

if [ -n "$PRESERVED_PROJECTS" ]; then
  PRESERVED_COUNT=$(printf '%s\n' "$PRESERVED_PROJECTS" | grep -c '^@' || true)
  echo "✓ Wrote $TARGET (preserved $PRESERVED_COUNT @include line(s) from Projects section)"
else
  echo "✓ Wrote $TARGET (fresh — no Projects @includes to preserve)"
fi
