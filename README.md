# claude-init — Personal Claude Code Plugin Marketplace

Personal Claude Code plugin marketplace maintained by [@bkirosangma](https://github.com/bkirosangma). This repo *is* the marketplace — install plugins individually via `claude plugin install <name>@claude-init`.

## Available plugins

| Plugin | What it does | Docs |
|---|---|---|
| **`init-workdir`** | Provision and maintain a multi-repo workspace: provider auth, gitconfig, ignore files, compound intelligence (graphify + claude-mem + MEMORY.md), knowledge vault, ui-ux-pro-max integration, group-organized repo cloning with self-hosted GitLab host detection, idempotent re-init, version-tracked manifest. Includes a `bootstrap` subcommand that installs everything for a fresh machine. | [plugins/init-workdir/README.md](plugins/init-workdir/README.md) |
| **`knowledge-base`** | `/kb` skill for managing knowledge-base vaults — architecture documents, design diagrams, ADRs, runbooks. **Full version** including music-domain features (SVG notation, guitar tabs, music archetype). Sub-commands: init, document, diagram, create, edit, svg, guitar-tabs, validate, transform. | [plugins/knowledge-base/README.md](plugins/knowledge-base/README.md) |
| **`hybrid-search`** | Fused search across claude-mem (temporal) + graphify (structural) using Reciprocal Rank Fusion. Ships the canonical compound-intelligence hook scripts (auto-rebuild-graph, crystallize, contradiction-check, decay, proceduralize, bump-relevance, Read-context injection). | [plugins/hybrid-search/README.md](plugins/hybrid-search/README.md) |
| **`compound-dispatch`** | Enriches subagent prompts with "Prior Knowledge" from graphify + claude-mem + MEMORY.md before dispatch. Closes the gap where subagents start with blank context. | [plugins/compound-dispatch/README.md](plugins/compound-dispatch/README.md) |

> Each plugin has its own README with detailed setup, config, and troubleshooting. This top-level README only covers one-time marketplace setup that all plugins share.

### Quick start — fresh machine

`init-workdir` is the recommended first install. Its `bootstrap` subcommand installs every external dependency (Homebrew packages, pipx graphify, npm uipro-cli, third-party Claude plugins) **and** copies the bundled `knowledge-base`, `hybrid-search`, `compound-dispatch` skills into `~/.claude/skills/<name>/` with the global hooks wired up. Three commands and the rest of the marketplace is ready:

```bash
# After registering the marketplace (Step 2 below):
claude plugin install init-workdir@claude-init
# In a claude session:
/init-workdir bootstrap        # installs CLIs, third-party plugins, bundled skills, global hooks
/init-workdir github           # provisions a workspace (or `gitlab`)
```

If you only want a single plugin (e.g. just `knowledge-base`), install it directly — `init-workdir`/`bootstrap` is optional.

---

## One-time marketplace setup

You only do this once. After this, installing any plugin from this repo is a single `claude plugin install` command.

### Prerequisites

| Tool | Check it works |
|---|---|
| **Claude Code CLI** | `claude --version` should print a version number |
| **git** | `git --version` |

If `claude` is missing, install Claude Code first: <https://docs.claude.com/en/docs/claude-code/getting-started>.

> Individual plugins may have additional prerequisites (e.g. python3, curl, MCP servers, API keys). Check the plugin's own README before installing it.

---

### Step 1 — Register the marketplace in Claude settings

Open `~/.claude/settings.json` (create it if missing) and add a `claude-init` entry under `extraKnownMarketplaces`:

```json
{
  "extraKnownMarketplaces": {
    "claude-init": {
      "source": {
        "source": "git",
        "url": "https://github.com/bkirosangma/claude-init.git",
        "ref": "main"
      }
    }
  }
}
```

If you have SSH set up for GitHub, you can use the SSH URL instead:

```json
"url": "git@github.com:bkirosangma/claude-init.git"
```

If you already have other marketplaces (e.g. `claude-plugins-official`), keep them and add `claude-init` alongside; don't replace the whole `extraKnownMarketplaces` object.

#### About the `ref` field

`"ref": "main"` tracks the `main` branch. New commits pushed to `main` reach you on the next `claude plugin update`. To pin a specific branch or tag, change the `ref` value.

---

### Step 2 — Install a plugin

```bash
claude plugin install <plugin-name>@claude-init
```

For example:

```bash
claude plugin install init-workdir@claude-init
```

Or, equivalently, start `claude` and use the slash command:

```bash
claude
# inside the session:
/plugin install init-workdir@claude-init
```

Verify it installed:

```bash
claude plugin list
# Should include: init-workdir@claude-init (enabled)
```

If you started a `claude` session before installing, **exit and restart** so it loads the new skill.

After install, follow the plugin's own README for first-run setup, config, and usage.

---

## Auto-update awareness

Every plugin in this marketplace ships with a `SessionStart` hook that silently checks if newer commits exist on the configured `ref`. When drift is detected, it prints a one-line nag at the start of your `claude` session telling you to run `claude plugin update`. If you're up to date, it's silent.

The check is cached for one hour and shared across all installed plugins from this marketplace, so installing multiple plugins doesn't mean multiple network calls per session.

---

## Marketplace-level troubleshooting

These cover issues common to all plugins. For plugin-specific issues, see that plugin's own README.

### `Failed to clone marketplace repository`

Your `settings.json` URL can't be reached. Two fixes:

1. **Switch to SSH** — change `url` in `settings.json` to `git@github.com:bkirosangma/claude-init.git`. This requires your GitHub SSH key to be set up.
2. **Use HTTPS** — change `url` to `https://github.com/bkirosangma/claude-init.git`. For private forks, embed a token: `https://<TOKEN>@github.com/bkirosangma/claude-init.git`.

### `/plugin isn't available in this environment.` or `Unknown command: /<skill>`

You're in Claude Desktop or another non-CLI Claude interface. The `/plugin` and skill slash commands only exist in the terminal-native `claude` CLI. Open a terminal and run `claude`.

### Plugin installed but the skill doesn't appear in slash list

Skills load at session start. After installing or updating, **exit your `claude` session and start a new one**.

### Updating to the latest version of a plugin

```bash
claude plugin update <plugin-name>@claude-init
# Then restart your claude session
```

---

## Repository layout

```
.claude-plugin/
  marketplace.json           # marketplace manifest, lists plugins[]
plugins/
  init-workdir/              # workspace coordinator + fresh-machine bootstrap
    .claude-plugin/plugin.json
    hooks/                   # canonical update-check hook (drop-in across all plugins)
    skills/init-workdir/
      SKILL.md               # router with bootstrap, github, gitlab, clone, update subcommands
      CHANGELOG.md           # newest-first; drives /init-workdir update diffs
      CODING_STANDARDS.md    # seeded into each provisioned workspace
      commands/              # one file per subcommand
      memory-seeds/          # MEMORY.md files copied into per-machine memory dir
    README.md

  knowledge-base/            # /kb skill — architecture docs, design diagrams, ADRs, music
    .claude-plugin/plugin.json
    hooks/
    skills/knowledge-base/
      SKILL.md
      archetypes/            # template structures (roadmaps, software-architecture, music)
      commands/              # init, document, diagram, create, edit, svg, guitar-tabs, validate, transform
      docs/                  # superpowers integration notes
      scripts/               # kb_*.py validation/migration/transform/music helpers + tests
    README.md

  hybrid-search/             # fused search + compound-intelligence hook scripts
    .claude-plugin/plugin.json
    hooks/
    skills/hybrid-search/
      SKILL.md
      hook.sh                # Read PreToolUse — graph + memory context injection
      auto-rebuild-graph.sh  # PostToolUse — graphify incremental rebuild
      crystallize.sh         # SessionEnd — crystallize observations
      proceduralize.py       # SessionEnd — extract workflow procedures
      contradiction-check.sh # observation-conflict detection
      bump-relevance.sh      # observation relevance counter
      decay.py               # Ebbinghaus decay over claude-mem
    README.md

  compound-dispatch/         # subagent prompt enricher
    .claude-plugin/plugin.json
    hooks/
    skills/compound-dispatch/
      SKILL.md
      gather-context.py      # builds Prior Knowledge from all 3 memory systems
    README.md
README.md                    # this file — marketplace overview
LICENSE
```

---

## License

[MIT](LICENSE)
