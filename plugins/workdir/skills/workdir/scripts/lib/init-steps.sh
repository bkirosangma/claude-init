#!/usr/bin/env bash
# init-steps.sh — sourceable library of idempotent workspace setup steps.
#
# Used by:
#   - scripts/init.sh   (runs every step)
#   - scripts/update.sh (runs the upgrade-relevant subset)
#
# Each function is idempotent: probes existing state, applies only what's missing, prints
# one status line per outcome. None of the functions are interactive — caller is responsible
# for any user prompts.

# Locate the skill root, regardless of who sources us.
_SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && cd .. && pwd)"
_TEMPLATES_DIR="$_SKILL_DIR/templates"
_SCRIPTS_DIR="$_SKILL_DIR/scripts"

# -----------------------------------------------------------------------------
# step_gitconfig <workdir> <provider> <name> <email>
# Writes <workdir>/.gitconfig (preserves existing user.name/user.email if both set)
# and adds includeIf to ~/.gitconfig.
# -----------------------------------------------------------------------------
step_gitconfig() {
  local workdir=$1 provider=$2 name=$3 email=$4
  local existing_name existing_email helper

  existing_name=$(git config -f "$workdir/.gitconfig" --get user.name 2>/dev/null || echo "")
  existing_email=$(git config -f "$workdir/.gitconfig" --get user.email 2>/dev/null || echo "")

  if [ -n "$existing_name" ] && [ -n "$existing_email" ]; then
    echo "✓ Gitconfig: $existing_name <$existing_email> (preserved)"
  else
    case "$provider" in
      github) helper="!gh auth git-credential" ;;
      gitlab) helper="store" ;;
      *) echo "ERROR: unknown provider $provider" >&2; return 2 ;;
    esac

    case "$provider" in
      github) local host="https://github.com" ;;
      gitlab) local host="https://gitlab.com" ;;
    esac

    cat > "$workdir/.gitconfig" <<EOF
[user]
    name = $name
    email = $email
[credential "$host"]
    helper = $helper
EOF
    echo "✓ Gitconfig written: $name <$email>"
  fi

  # Wire ~/.gitconfig includeIf if not already present
  if grep -qF "gitdir:${workdir}" ~/.gitconfig 2>/dev/null; then
    echo "✓ ~/.gitconfig includeIf: already present"
  else
    printf '\n[includeIf "gitdir:%s/"]\n    path = %s/.gitconfig\n' "$workdir" "$workdir" >> ~/.gitconfig
    echo "✓ ~/.gitconfig includeIf: added for $workdir"
  fi
}

# -----------------------------------------------------------------------------
# step_ignores <workdir>
# Appends any missing entries to .gitignore, .claudeignore, .graphifyignore.
# -----------------------------------------------------------------------------
step_ignores() {
  local workdir=$1

  _ensure_line "$workdir/.gitignore" \
    "# Graphify generated output" "graphify-out/" "" \
    "# Claude Code project settings" ".claude/" "" \
    "# workdir state manifest" ".workdir/"

  _ensure_line "$workdir/.claudeignore" \
    "# Graphify generated output (large JSON/HTML — use GRAPH_REPORT.md instead)" \
    "graphify-out/*.html" "graphify-out/graph.json" "graphify-out/cypher.txt" "graphify-out/.graphify_*"

  _ensure_line "$workdir/.graphifyignore" \
    "# Test fixtures and snapshots" "**/__snapshots__/" "**/fixtures/" "**/testdata/" "" \
    "# Large data files" "*.csv" "*.parquet" "*.sqlite" "" \
    "# IDE settings" ".idea/" ".vscode/" "*.iml" "" \
    "# Lock files (all stacks)" "package-lock.json" "yarn.lock" "bun.lock" "pnpm-lock.yaml" "poetry.lock" "Pipfile.lock" "" \
    "# Generated/compiled artifacts" "*.min.js" "*.min.css" "*.generated.*" "*.class" "*.pyc" "*.pyo"

  echo "✓ Ignore files: .gitignore, .claudeignore, .graphifyignore (entries appended as needed)"
}

# Helper: append each line to <file> unless an exact line match already exists.
# Blank-line args become blank lines (only inserted if file is fresh; preserves spacing).
_ensure_line() {
  local file=$1; shift
  if [ ! -f "$file" ]; then : > "$file"; fi
  for line in "$@"; do
    if [ -z "$line" ]; then
      # Insert blank line only if file doesn't already end in one
      if [ -s "$file" ] && [ -n "$(tail -c1 "$file")" ]; then
        echo "" >> "$file"
      fi
      continue
    fi
    if ! grep -qFx -- "$line" "$file" 2>/dev/null; then
      echo "$line" >> "$file"
    fi
  done
}

# -----------------------------------------------------------------------------
# step_graphify_hook <workdir>
# -----------------------------------------------------------------------------
step_graphify_hook() {
  local workdir=$1
  if [ -f "$workdir/.claude/settings.json" ] && grep -q graphify "$workdir/.claude/settings.json" 2>/dev/null; then
    echo "✓ graphify hook: present in $workdir/.claude/settings.json"
    return 0
  fi
  export PATH="$HOME/.local/bin:$PATH"
  (cd "$workdir" && graphify claude install >/dev/null 2>&1) \
    && echo "✓ graphify hook: installed" \
    || echo "⚠ graphify hook: install failed (run 'graphify claude install' from $workdir manually)"
}

# -----------------------------------------------------------------------------
# step_coding_standards <workdir>
# -----------------------------------------------------------------------------
step_coding_standards() {
  local workdir=$1
  local skill_standards="$_SKILL_DIR/CODING_STANDARDS.md"
  if [ ! -f "$skill_standards" ]; then
    echo "⚠ CODING_STANDARDS.md: skill copy missing ($skill_standards) — skipping"
    return 0
  fi
  if [ -f "$workdir/CODING_STANDARDS.md" ]; then
    echo "✓ CODING_STANDARDS.md: exists (preserved)"
  else
    cp "$skill_standards" "$workdir/CODING_STANDARDS.md"
    echo "✓ CODING_STANDARDS.md: copied"
  fi
}

# -----------------------------------------------------------------------------
# step_render_claude_md <workdir> <provider> <name> <email>
# -----------------------------------------------------------------------------
step_render_claude_md() {
  local workdir=$1 provider=$2 name=$3 email=$4
  bash "$_SCRIPTS_DIR/render-claude-md.sh" "$workdir" "$provider" "$name" "$email"
}

# -----------------------------------------------------------------------------
# step_claude_mem_worker
# -----------------------------------------------------------------------------
step_claude_mem_worker() {
  [ -s "$HOME/.nvm/nvm.sh" ] && source "$HOME/.nvm/nvm.sh" && nvm use 22 >/dev/null 2>&1 || true
  export PATH="$HOME/.bun/bin:$PATH"
  if npx claude-mem status >/dev/null 2>&1; then
    echo "✓ claude-mem worker: running"
  else
    npx claude-mem start >/dev/null 2>&1 \
      && echo "✓ claude-mem worker: started" \
      || echo "⚠ claude-mem worker: failed to start (run 'npx claude-mem start' manually)"
  fi
}

# -----------------------------------------------------------------------------
# step_uipro <workdir>
# Installs uipro-cli globally if missing, then runs 'uipro init --ai claude' in the workdir.
# -----------------------------------------------------------------------------
step_uipro() {
  local workdir=$1
  export PATH="$HOME/.bun/bin:$PATH"
  # Source nvm so npm-global binaries (installed under the active node version) are on PATH.
  [ -s "$HOME/.nvm/nvm.sh" ] && source "$HOME/.nvm/nvm.sh" >/dev/null 2>&1 && nvm use 22 >/dev/null 2>&1 || true
  if ! command -v uipro >/dev/null 2>&1; then
    echo "+ uipro-cli: missing — installing globally via npm"
    npm install -g uipro-cli >/dev/null 2>&1 || {
      echo "⚠ uipro-cli: install failed (run 'npm install -g uipro-cli' manually)"
      return 0
    }
  fi
  if [ -d "$workdir/.claude/skills/ui-ux-pro-max" ]; then
    echo "✓ ui-ux-pro-max skill: present at $workdir/.claude/skills/ui-ux-pro-max"
  else
    (cd "$workdir" && uipro init --ai claude >/dev/null 2>&1) \
      && echo "✓ ui-ux-pro-max skill: installed" \
      || echo "⚠ ui-ux-pro-max skill: install failed (run 'uipro init --ai claude' from $workdir manually)"
  fi
}

# -----------------------------------------------------------------------------
# step_memory_seeds <workdir>
# Copies seeds from skill into the workspace's per-machine memory dir.
# -----------------------------------------------------------------------------
step_memory_seeds() {
  local workdir=$1
  local seeds_dir="$_SKILL_DIR/memory-seeds"
  if [ ! -d "$seeds_dir" ]; then
    echo "⚠ memory seeds: no seeds shipped — skipping"
    return 0
  fi

  local memory_dir
  memory_dir=$(WORKDIR="$workdir" python3 -c '
import os, re
workdir = os.path.realpath(os.environ["WORKDIR"])
encoded = re.sub(r"[^A-Za-z0-9]", "-", workdir)
print(os.path.expanduser(f"~/.claude/projects/{encoded}/memory"))
')

  mkdir -p "$memory_dir"
  touch "$memory_dir/MEMORY.md"

  local copied=0 preserved=0
  for seed in "$seeds_dir"/*.md; do
    [ -f "$seed" ] || continue
    local basename name desc index_line
    basename=$(basename "$seed")
    if [ -f "$memory_dir/$basename" ]; then
      preserved=$((preserved + 1))
      continue
    fi
    cp "$seed" "$memory_dir/$basename"
    name=$(awk -F': ' '/^name:/ {print $2; exit}' "$seed")
    desc=$(awk -F': ' '/^description:/ {print $2; exit}' "$seed")
    index_line="- [$name]($basename) — $desc"
    if ! grep -qF "($basename)" "$memory_dir/MEMORY.md" 2>/dev/null; then
      echo "$index_line" >> "$memory_dir/MEMORY.md"
    fi
    copied=$((copied + 1))
  done

  echo "✓ memory seeds: $copied copied, $preserved preserved (dir: $memory_dir)"
}

# -----------------------------------------------------------------------------
# step_verify_prereqs <provider>
# Probes the provider CLI and the compound intelligence stack. Returns 0 if all OK, 1 if any
# missing. Prints status for every probe regardless.
# -----------------------------------------------------------------------------
step_verify_prereqs() {
  local provider=$1
  local missing=0

  export PATH="$HOME/.local/bin:$HOME/.bun/bin:$PATH"
  [ -s "$HOME/.nvm/nvm.sh" ] && source "$HOME/.nvm/nvm.sh" >/dev/null 2>&1 || true

  case "$provider" in
    github)
      if command -v gh >/dev/null 2>&1; then
        echo "✓ gh: $(gh --version | head -1)"
      else
        echo "✗ gh: MISSING — brew install gh"; missing=1
      fi ;;
    gitlab)
      if command -v glab >/dev/null 2>&1; then
        echo "✓ glab: $(glab --version | head -1)"
      else
        echo "✗ glab: MISSING — brew install glab"; missing=1
      fi ;;
    *) echo "ERROR: unknown provider $provider" >&2; return 2 ;;
  esac

  command -v graphify >/dev/null 2>&1 && echo "✓ graphify: OK" \
    || { echo "✗ graphify: MISSING — pipx install graphifyy"; missing=1; }

  command -v bun >/dev/null 2>&1 && echo "✓ bun: $(bun --version)" \
    || { echo "✗ bun: MISSING — curl -fsSL https://bun.sh/install | bash"; missing=1; }

  if node --version 2>/dev/null | grep -qE 'v(2[2-9]|[3-9][0-9])'; then
    echo "✓ node: $(node --version)"
  else
    echo "✗ node: MISSING or <22 — nvm install 22"; missing=1
  fi

  grep -q '"claude-mem@thedotmack"' ~/.claude/settings.json 2>/dev/null \
    && echo "✓ claude-mem plugin: OK" \
    || { echo "✗ claude-mem plugin: MISSING — claude plugins add claude-mem@thedotmack"; missing=1; }

  grep -q '"superpowers@claude-plugins-official"' ~/.claude/settings.json 2>/dev/null \
    && echo "✓ superpowers plugin: OK" \
    || { echo "✗ superpowers plugin: MISSING — claude plugins add superpowers@claude-plugins-official"; missing=1; }

  grep -q 'hybrid-search/hook.sh' ~/.claude/settings.json 2>/dev/null \
    && echo "✓ hybrid-search hooks: OK" \
    || { echo "✗ hybrid-search hooks: MISSING — run /workdir bootstrap"; missing=1; }

  test -f ~/.claude/skills/knowledge-base/SKILL.md \
    && echo "✓ knowledge-base skill: OK" \
    || { echo "✗ knowledge-base skill: MISSING — run /workdir bootstrap"; missing=1; }

  return $missing
}

# -----------------------------------------------------------------------------
# step_detect_prior <workdir>
# Reads the manifest and sets globals PRIOR_VERSION, PRIOR_AT, STATE (NEW|UPGRADE|LEGACY).
# -----------------------------------------------------------------------------
step_detect_prior() {
  local workdir=$1
  local manifest="$workdir/.workdir/state.json"

  if [ -f "$manifest" ]; then
    PRIOR_VERSION=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["skillVersion"])' "$manifest" 2>/dev/null || echo "")
    PRIOR_AT=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("appliedAt",""))' "$manifest" 2>/dev/null || echo "")
    STATE="UPGRADE"
  elif grep -q 'Multi-Repo Workspace' "$workdir/CLAUDE.md" 2>/dev/null; then
    PRIOR_VERSION="legacy"
    PRIOR_AT=""
    STATE="LEGACY"
  else
    PRIOR_VERSION=""
    PRIOR_AT=""
    STATE="NEW"
  fi
}
