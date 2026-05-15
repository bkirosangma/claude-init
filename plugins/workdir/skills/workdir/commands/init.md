# Init Command

Initialize the current working directory as a multi-repo workspace with the full compound
intelligence stack.

Accepts `provider` from the router: `github` or `gitlab`.

The mechanical work is done by `scripts/init.sh`. This command file orchestrates the
interactive steps (prereqs surfacing, provider auth, gitconfig name/email prompts, vault
init via the `knowledge-base` skill, optional graph build prompt) and calls the script to
run the rest.

---

## Step 1 — Verify Prerequisites

```bash
source ~/.claude/skills/workdir/scripts/lib/init-steps.sh
step_verify_prereqs <provider>
```

If any line is `✗ MISSING`, stop and surface the install commands to the user. Do NOT proceed
until all prerequisites are present. Suggest `/workdir bootstrap` if multiple are missing.

---

## Step 2 — Authenticate

```bash
case "<provider>" in
  github) gh auth status 2>&1 ;;
  gitlab) glab auth status 2>&1 ;;
esac
```

If not authenticated, instruct the user to run the login command themselves (it's interactive
and the bash tool can't drive it):

**GitHub** — tell the user to run:
```
! gh auth login
```
Select: GitHub.com → HTTPS → Yes (authenticate git) → Login with a web browser

**GitLab** — tell the user to run:
```
! glab auth login
```

After they confirm it's done, verify with `auth status` again before continuing.

---

## Step 3 — Locate Workspace & Detect Prior Init

```bash
source ~/.claude/skills/workdir/scripts/lib/find-workdir.sh --soft  # fresh-init fallback to $(pwd)
source ~/.claude/skills/workdir/scripts/lib/init-steps.sh
step_detect_prior "$WORKDIR"   # sets PRIOR_VERSION, PRIOR_AT, STATE
CURRENT_VERSION=$(awk '/^version:/{print $2; exit}' ~/.claude/skills/workdir/SKILL.md)
```

If `STATE` is `UPGRADE` or `LEGACY` and `PRIOR_VERSION != CURRENT_VERSION`, print the
changelog diff:

```bash
bash ~/.claude/skills/workdir/scripts/lib/changelog-diff.sh "$PRIOR_VERSION"
```

Then confirm via `AskUserQuestion`:

| State | Prompt |
|-------|--------|
| `NEW` | "Initialize workspace at `<WORKDIR>`?" |
| `UPGRADE` (same version) | "Workspace already at `$CURRENT_VERSION`. Re-run all steps to verify state?" |
| `UPGRADE` (older version) | "Upgrade workspace from `$PRIOR_VERSION` → `$CURRENT_VERSION`?" |
| `LEGACY` | "Workspace exists but has no manifest. Run all idempotent steps and write the manifest?" |

If the user declines, exit cleanly.

---

## Step 4 — Gitconfig identity (interactive)

Probe existing config before prompting:

```bash
EXISTING_NAME=$(git config -f "$WORKDIR/.gitconfig" --get user.name 2>/dev/null || echo "")
EXISTING_EMAIL=$(git config -f "$WORKDIR/.gitconfig" --get user.email 2>/dev/null || echo "")
```

If both are set, reuse them silently (`NAME="$EXISTING_NAME"`, `EMAIL="$EXISTING_EMAIL"`).
Otherwise ask via `AskUserQuestion`:

> "What name should git use for commits in this workspace?"
> "What email address?"

Store the answers as `$NAME` and `$EMAIL`.

---

## Step 5 — Run the mechanical script

```bash
bash ~/.claude/skills/workdir/scripts/init.sh "$WORKDIR" "<provider>" "$NAME" "$EMAIL"
```

The script handles:

| Step | What |
|---|---|
| Gitconfig | Writes `$WORKDIR/.gitconfig`, wires `~/.gitconfig` includeIf |
| Ignore files | `.gitignore`, `.claudeignore`, `.graphifyignore` — append-only, preserves existing |
| Graphify hook | Installs PreToolUse hook to `$WORKDIR/.claude/settings.json` |
| Coding standards | Copies `CODING_STANDARDS.md` (preserves existing) |
| CLAUDE.md | Renders from `templates/workspace-CLAUDE.md.template`, preserves `## Projects` @includes |
| claude-mem worker | Starts if not running |
| ui-ux-pro-max | `uipro init --ai claude` at workspace level |
| Memory seeds | Copies seeds into `~/.claude/projects/<encoded-workdir>/memory/` |
| Manifest | Writes `$WORKDIR/.workdir/state.json` |

Show the script's stdout to the user.

---

## Step 6 — Initialize Knowledge Vault

```bash
mkdir -p "$WORKDIR/knowledgebase"
```

If `$WORKDIR/knowledgebase/.archdesigner/config.json` already exists, skip. Otherwise invoke
the knowledge-base skill:

```
/knowledge-base init <WORKDIR>/knowledgebase
```

This is a SKILL invocation (not a bash command) — dispatch through the Skill tool.

---

## Step 7 — Build Initial Knowledge Graph (Optional)

If graphify is available and repos are already cloned under `<group>/<repo>/`, ask via
`AskUserQuestion`:

> "Build the initial cross-repo knowledge graph now? Takes a few minutes for large codebases."

If yes:

```bash
cd "$WORKDIR" && export PATH="$HOME/.local/bin:$PATH" && graphify . --update
```

If no, the auto-rebuild hook will index code on Write/Edit.

---

## Step 8 — Summary

Print a final summary to the user combining what `init.sh` reported with the vault init and
graph build results from Steps 6–7. Next-step suggestions:

```
Next steps:
  Clone a repo:        /workdir clone <url>
  Clone with group:    /workdir clone <url> --group <name>
  Pull all repos:      /workdir pull
  Build graph:         /graphify .
  Search memory:       /mem-search "query"
  Fused search:        /hybrid-search "topic"
  New document:        /kb document "<topic>"
  New diagram:         /kb diagram "<topic>"
```

---

## What lives where (for editing this skill)

| Layer | File | Purpose |
|---|---|---|
| Routing | `commands/init.md` (this file) | Interactive orchestration |
| Mechanical | `scripts/init.sh` | Runs every idempotent step |
| Step library | `scripts/lib/init-steps.sh` | Sourced by init.sh AND update.sh |
| CLAUDE.md content | `templates/workspace-CLAUDE.md.template` | Single source of truth for the rendered CLAUDE.md |
| Render logic | `scripts/render-claude-md.sh` | Placeholder substitution + `## Projects` preservation |
| Helpers | `scripts/lib/find-workdir.sh`, `write-manifest.sh`, `changelog-diff.sh` | Reused across commands |

To add a new step: define a function in `lib/init-steps.sh`, call it from `init.sh`, and
(if it should also run on update) reference it from `scripts/update.sh`.
