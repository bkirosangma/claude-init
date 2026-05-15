#!/usr/bin/env bash
# bootstrap.sh — fresh-machine setup for /workdir.
#
# Installs Homebrew packages, npm globals, pipx packages, third-party Claude Code plugins,
# copies bundled skills into ~/.claude/skills/, and wires global hooks into ~/.claude/settings.json.
# Idempotent: re-runs cleanly. Pass --force to overwrite existing local skill copies.
#
# Usage:
#   bootstrap.sh             # idempotent: preserve existing local skill copies
#   bootstrap.sh --force     # overwrite existing local skill copies
#
# Driven by ~/.claude/skills/workdir/commands/bootstrap.md (user confirmation happens there).

set -uo pipefail
# No `set -e` — per-step failures must be isolated and reported, not abort the whole run.

FORCE=false
[ "${1:-}" = "--force" ] && FORCE=true

# ------------------------------------------------------------------------------
# Step 1 — Verify Homebrew
# ------------------------------------------------------------------------------
if ! command -v brew >/dev/null 2>&1; then
  echo "ERROR: Homebrew is required but missing."
  echo "Install via: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
  echo "Then re-run /workdir bootstrap."
  exit 1
fi
echo "✓ brew $(brew --version | head -1)"

# ------------------------------------------------------------------------------
# Step 2 — External CLIs (gh, glab, bun, Node 22+, pipx)
# ------------------------------------------------------------------------------
for tool in gh glab; do
  if command -v "$tool" >/dev/null 2>&1; then
    echo "✓ $tool $($tool --version 2>&1 | head -1)"
  else
    echo "+ Installing $tool"
    brew install "$tool"
  fi
done

if command -v bun >/dev/null 2>&1; then
  echo "✓ bun $(bun --version)"
else
  echo "+ Installing bun"
  curl -fsSL https://bun.sh/install | bash
  export PATH="$HOME/.bun/bin:$PATH"
fi

# Source nvm if it exists, so a freshly-installed node is on PATH for the rest of this run
[ -s "$HOME/.nvm/nvm.sh" ] && source "$HOME/.nvm/nvm.sh"

if command -v node >/dev/null 2>&1 && node --version | grep -qE 'v(2[2-9]|[3-9][0-9])'; then
  echo "✓ node $(node --version)"
else
  echo "+ Installing Node 22 via nvm"
  if [ ! -d "$HOME/.nvm" ]; then
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
    source "$HOME/.nvm/nvm.sh"
  fi
  nvm install 22
  nvm use 22
fi

if command -v pipx >/dev/null 2>&1; then
  echo "✓ pipx $(pipx --version)"
else
  echo "+ Installing pipx"
  brew install pipx
  pipx ensurepath
fi

# ------------------------------------------------------------------------------
# Step 3 — graphify CLI + skill
# ------------------------------------------------------------------------------
export PATH="$HOME/.local/bin:$PATH"

if command -v graphify >/dev/null 2>&1; then
  echo "✓ graphify $(graphify --version 2>&1 | head -1 || echo installed)"
else
  echo "+ Installing graphify"
  pipx install graphifyy
fi

graphify install --platform claude
echo "✓ graphify skill installed via 'graphify install --platform claude'"

# ------------------------------------------------------------------------------
# Step 4 — uipro-cli
# ------------------------------------------------------------------------------
if command -v uipro >/dev/null 2>&1; then
  echo "✓ uipro $(uipro --version 2>&1 | head -1)"
else
  echo "+ Installing uipro-cli"
  npm install -g uipro-cli
fi

# ------------------------------------------------------------------------------
# Step 5 — Third-party Claude Code plugins
# ------------------------------------------------------------------------------
if grep -q '"claude-mem@thedotmack"' ~/.claude/settings.json 2>/dev/null; then
  echo "✓ claude-mem plugin: PRESENT"
else
  echo "+ Adding claude-mem plugin"
  claude plugins add claude-mem@thedotmack
fi

if grep -q '"superpowers@claude-plugins-official"' ~/.claude/settings.json 2>/dev/null; then
  echo "✓ superpowers plugin: PRESENT"
else
  echo "+ Adding superpowers plugin"
  claude plugins add superpowers@claude-plugins-official
fi

# ------------------------------------------------------------------------------
# Step 6 — Copy bundled claude-init skills into ~/.claude/skills/
# ------------------------------------------------------------------------------
MARKETPLACE_DIR="$HOME/.claude/plugins/marketplaces/claude-init"

if [ ! -d "$MARKETPLACE_DIR" ]; then
  echo "ERROR: claude-init marketplace not registered yet."
  echo "Add to ~/.claude/settings.json under 'extraKnownMarketplaces' first, restart Claude Code,"
  echo "then re-run /workdir bootstrap."
  exit 1
fi

for skill in knowledge-base hybrid-search compound-dispatch; do
  PLUGIN_SKILL="$MARKETPLACE_DIR/plugins/$skill/skills/$skill"
  TARGET="$HOME/.claude/skills/$skill"

  if [ ! -d "$PLUGIN_SKILL" ]; then
    echo "⚠ $skill: marketplace clone missing — has the marketplace been refreshed?"
    continue
  fi

  if [ -d "$TARGET" ] && [ "$FORCE" = false ]; then
    echo "✓ $skill: already at $TARGET (preserved — pass --force to overwrite)"
    continue
  fi

  if [ -d "$TARGET" ] && [ "$FORCE" = true ]; then
    rm -rf "$TARGET"
    cp -r "$PLUGIN_SKILL" "$TARGET"
    find "$TARGET" -name "*.sh" -exec chmod +x {} \;
    echo "✓ $skill: replaced (forced)"
  else
    cp -r "$PLUGIN_SKILL" "$TARGET"
    find "$TARGET" -name "*.sh" -exec chmod +x {} \;
    echo "✓ $skill: copied to $TARGET"
  fi
done

# ------------------------------------------------------------------------------
# Step 7 — Wire global hooks in ~/.claude/settings.json
# ------------------------------------------------------------------------------
python3 - <<'PY'
import json
from pathlib import Path

settings_path = Path.home() / ".claude" / "settings.json"
settings_path.parent.mkdir(parents=True, exist_ok=True)
if settings_path.exists():
    settings = json.loads(settings_path.read_text())
else:
    settings = {}

settings.setdefault("hooks", {})

DESIRED_HOOKS = {
    "PreToolUse": [
        {"matcher": "Read",
         "hooks": [{"type": "command", "command": "~/.claude/skills/hybrid-search/hook.sh"}]},
    ],
    "PostToolUse": [
        {"matcher": "Write|Edit|Bash",
         "hooks": [{"type": "command", "command": "~/.claude/skills/hybrid-search/auto-rebuild-graph.sh"}]},
        {"matcher": "mcp__plugin_claude-mem_mcp-search__get_observations",
         "hooks": [{"type": "command", "command": "~/.claude/skills/hybrid-search/bump-relevance.sh"}]},
        {"matcher": "*",
         "hooks": [{"type": "command", "command": "~/.claude/skills/hybrid-search/contradiction-check.sh"}]},
    ],
    "SessionEnd": [
        {"matcher": "*",
         "hooks": [{"type": "command", "command": "~/.claude/skills/hybrid-search/crystallize.sh"}]},
        {"matcher": "*",
         "hooks": [{"type": "command", "command": "python3 ~/.claude/skills/hybrid-search/proceduralize.py"}]},
    ],
}

added = 0
for event, configs in DESIRED_HOOKS.items():
    existing = settings["hooks"].setdefault(event, [])
    existing_cmds = {h.get("command") for cfg in existing for h in cfg.get("hooks", [])}
    for cfg in configs:
        new_cmds = [h["command"] for h in cfg["hooks"]]
        if any(c in existing_cmds for c in new_cmds):
            continue
        existing.append(cfg)
        added += 1

settings_path.write_text(json.dumps(settings, indent=2))
print(f"✓ Wrote ~/.claude/settings.json (+{added} hook configs)")
PY

# ------------------------------------------------------------------------------
# Step 8 — Summary
# ------------------------------------------------------------------------------
cat <<EOF

Bootstrap complete.

Installed / verified:
  ✓ External CLIs:     gh, glab, bun, node 22+, pipx
  ✓ graphify CLI:      pipx
  ✓ graphify skill:    ~/.claude/skills/graphify/
  ✓ uipro CLI:         npm global
  ✓ claude-mem:        plugin added
  ✓ superpowers:       plugin added
  ✓ knowledge-base:    ~/.claude/skills/knowledge-base/
  ✓ hybrid-search:     ~/.claude/skills/hybrid-search/  (with hook scripts)
  ✓ compound-dispatch: ~/.claude/skills/compound-dispatch/
  ✓ Global hooks:      ~/.claude/settings.json

Next:
  /workdir init gitlab    # provision a workspace
  /workdir init github    # or with GitHub
EOF
