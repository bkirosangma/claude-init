# Bootstrap Command

Set up everything `workdir` depends on for a fresh-machine first run. After bootstrap,
`/workdir init <github|gitlab>` should pass all prerequisite checks immediately.

**Run this once per machine, before the first `/workdir init <provider>`.**

What gets installed:

| Layer | What | How |
|---|---|---|
| **External CLIs** | `gh`, `glab`, `bun`, Node 22+, `pipx`, `npm` | brew + curl + nvm |
| **graphify** | Cross-repo structural graph engine | `pipx install graphifyy` + `graphify install --platform claude` |
| **uipro-cli** | UI/UX Pro Max distributor | `npm install -g uipro-cli` |
| **Third-party plugins** | `claude-mem@thedotmack`, `superpowers@claude-plugins-official` | `claude plugins add` |
| **Bundled skills** | `knowledge-base`, `hybrid-search`, `compound-dispatch` | Copy from claude-init marketplace clone into `~/.claude/skills/` |
| **Global hooks** | hybrid-search Read injector, auto-rebuild-graph, crystallize, contradiction-check, proceduralize, bump-relevance | Idempotent JSON merge into `~/.claude/settings.json` |

---

## Step 1 — Confirm scope

Print the list above and ask:

> "Run bootstrap? This will install Homebrew packages, npm globals, pipx packages, third-party
> Claude Code plugins, and write hook entries to `~/.claude/settings.json`. Existing files are
> preserved unless you pass `--force`. Continue?"

If no, exit cleanly. If yes, proceed.

---

## Step 2 — Verify Homebrew

```bash
if ! command -v brew >/dev/null 2>&1; then
  echo "ERROR: Homebrew is required but missing."
  echo "Install via: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
  echo "Then re-run /workdir bootstrap."
  exit 1
fi
echo "✓ brew $(brew --version | head -1)"
```

---

## Step 3 — Install External CLIs

Each step probes first; only installs what's missing.

```bash
# gh + glab — provider CLIs
for tool in gh glab; do
  if command -v "$tool" >/dev/null 2>&1; then
    echo "✓ $tool $($tool --version 2>&1 | head -1)"
  else
    echo "+ Installing $tool"
    brew install "$tool"
  fi
done

# bun
if command -v bun >/dev/null 2>&1; then
  echo "✓ bun $(bun --version)"
else
  echo "+ Installing bun"
  curl -fsSL https://bun.sh/install | bash
  export PATH="$HOME/.bun/bin:$PATH"
fi

# Node 22+ via nvm
if command -v node >/dev/null 2>&1 && node --version | grep -qE 'v(2[2-9]|[3-9][0-9])'; then
  echo "✓ node $(node --version)"
else
  echo "+ Installing Node 22 via nvm"
  if [ ! -d "$HOME/.nvm" ]; then
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
  fi
  source "$HOME/.nvm/nvm.sh"
  nvm install 22
  nvm use 22
fi

# pipx (for graphify)
if command -v pipx >/dev/null 2>&1; then
  echo "✓ pipx $(pipx --version)"
else
  echo "+ Installing pipx"
  brew install pipx
  pipx ensurepath
fi
```

---

## Step 4 — Install graphify and the graphify skill

```bash
export PATH="$HOME/.local/bin:$PATH"

if command -v graphify >/dev/null 2>&1; then
  echo "✓ graphify $(graphify --version 2>&1 | head -1 || echo installed)"
else
  echo "+ Installing graphify"
  pipx install graphifyy
fi

# Self-installs the graphify skill into ~/.claude/skills/graphify/
graphify install --platform claude
echo "✓ graphify skill installed via 'graphify install --platform claude'"
```

---

## Step 5 — Install uipro-cli

```bash
if command -v uipro >/dev/null 2>&1; then
  echo "✓ uipro $(uipro --version 2>&1 | head -1)"
else
  echo "+ Installing uipro-cli"
  npm install -g uipro-cli
fi
```

The `uipro init --ai claude` step (which writes the actual ui-ux-pro-max skill into Claude
Code) runs as part of the workspace init flow (Step 12 of `commands/init.md`), not here.

---

## Step 6 — Add third-party Claude Code plugins

```bash
# claude-mem (temporal memory)
if grep -q '"claude-mem@thedotmack"' ~/.claude/settings.json 2>/dev/null; then
  echo "✓ claude-mem plugin: PRESENT"
else
  echo "+ Adding claude-mem plugin"
  claude plugins add claude-mem@thedotmack
fi

# superpowers (workflow intelligence)
if grep -q '"superpowers@claude-plugins-official"' ~/.claude/settings.json 2>/dev/null; then
  echo "✓ superpowers plugin: PRESENT"
else
  echo "+ Adding superpowers plugin"
  claude plugins add superpowers@claude-plugins-official
fi
```

---

## Step 7 — Copy bundled claude-init skills into `~/.claude/skills/`

The hooks installed in Step 8 reference `~/.claude/skills/<name>/<script>` — the canonical
local skills path. Copy each bundled skill from the marketplace clone there.

```bash
MARKETPLACE_DIR=~/.claude/plugins/marketplaces/claude-init

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

  if [ -d "$TARGET" ]; then
    echo "✓ $skill: already at $TARGET (preserved — pass --force to overwrite)"
    continue
  fi

  cp -r "$PLUGIN_SKILL" "$TARGET"
  # Make scripts executable
  find "$TARGET" -name "*.sh" -exec chmod +x {} \;
  echo "✓ $skill: copied to $TARGET"
done
```

If `--force` was passed, replace the target dir instead of preserving:

```bash
if [ "$1" = "--force" ]; then
  rm -rf "$TARGET"
  cp -r "$PLUGIN_SKILL" "$TARGET"
  echo "✓ $skill: replaced (forced)"
fi
```

---

## Step 8 — Wire Global Hooks in `~/.claude/settings.json`

Idempotent JSON merge — preserves any hooks the user has already configured, only adds the
ones missing.

```bash
python3 - <<'PY'
import json, os
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
```

If the user has custom hooks already pointing at the same script paths, they're preserved —
the merge only adds missing entries.

---

## Step 9 — Summary

```
Bootstrap complete.

Installed / verified:
  ✓ External CLIs:    gh, glab, bun, node 22+, pipx
  ✓ graphify CLI:     pipx
  ✓ graphify skill:   ~/.claude/skills/graphify/
  ✓ uipro CLI:        npm global
  ✓ claude-mem:       plugin added
  ✓ superpowers:      plugin added
  ✓ knowledge-base:   ~/.claude/skills/knowledge-base/
  ✓ hybrid-search:    ~/.claude/skills/hybrid-search/  (with hook scripts)
  ✓ compound-dispatch: ~/.claude/skills/compound-dispatch/
  ✓ Global hooks:     ~/.claude/settings.json

Next:
  /workdir init gitlab    # provision a workspace
  /workdir init github    # or with GitHub
```

---

## Failure modes

| Symptom | Fix |
|---|---|
| `brew: command not found` | Install Homebrew first (Step 2 prints the command) |
| `marketplace not registered` | Add `extraKnownMarketplaces` entry to `~/.claude/settings.json`, restart Claude Code |
| `claude plugins add` interactive prompt | Approve the plugin install when prompted; idempotent on re-run |
| `pipx install graphifyy` fails | Ensure pipx is on PATH (`pipx ensurepath` then restart shell) |
| Hooks already exist with different paths | The merge preserves them — bootstrap only adds missing entries |
| Want to overwrite an existing local skill copy | Re-run `/workdir bootstrap --force` |
