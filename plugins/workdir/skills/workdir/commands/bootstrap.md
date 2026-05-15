# Bootstrap Command

Set up everything `workdir` depends on for a fresh-machine first run. After bootstrap,
`/workdir init <github|gitlab>` should pass all prerequisite checks immediately.

**Run this once per machine, before the first `/workdir init <provider>`.**

The mechanical work is done by `scripts/bootstrap.sh`. This command file only handles the
user confirmation and surfaces the script's output.

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

## Step 1 — Confirm

Print the table above and ask via `AskUserQuestion`:

> "Run bootstrap? This installs Homebrew packages, npm globals, pipx packages, third-party
> Claude Code plugins, and writes hook entries to `~/.claude/settings.json`. Existing files
> are preserved unless you re-run with `--force`."

If the user declines, exit cleanly. If they confirm, proceed.

---

## Step 2 — Run bootstrap.sh

```bash
bash ~/.claude/skills/workdir/scripts/bootstrap.sh
```

For a forced re-install (overwrite existing local skill copies):

```bash
bash ~/.claude/skills/workdir/scripts/bootstrap.sh --force
```

Show the script's stdout to the user verbatim. The script:

- Probes each dependency before installing; skips what's already present
- Continues past per-step failures and reports them in the final summary
- Hard-fails only on missing Homebrew (Step 1) or missing marketplace clone (Step 6)
- Sets `GIT_TERMINAL_PROMPT=0`-equivalent: never blocks waiting for interactive input

---

## Step 3 — Handle failures

If the script exits non-zero, the cause is one of:

| Symptom | Fix |
|---|---|
| `brew: command not found` | Install Homebrew first (the script prints the install command) |
| `claude-init marketplace not registered yet` | Add `extraKnownMarketplaces` entry to `~/.claude/settings.json`, restart Claude Code |
| `claude plugins add` interactive prompt | Approve the plugin install when prompted; idempotent on re-run |
| `pipx install graphifyy` fails | Ensure pipx is on PATH (`pipx ensurepath` then restart shell) |
| Hooks already exist with different paths | The merge preserves them — bootstrap only adds missing entries |
| Want to overwrite an existing local skill copy | Re-run `/workdir bootstrap --force` |

Surface the relevant fix to the user. Do not auto-retry — the user has to take the manual step
first.
