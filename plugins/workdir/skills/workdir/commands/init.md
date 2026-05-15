# Init Command

Initialize the current working directory as a multi-repo workspace with the full compound
intelligence stack, scoped to the workspace level rather than a single project.

Accepts `provider` from the router: `github` or `gitlab`.

---

## Step 1 — Verify All Prerequisites

Check both the provider CLI and the compound intelligence stack.

```bash
export PATH="$HOME/.local/bin:$HOME/.bun/bin:$PATH"

# Provider CLI
case "<provider>" in
  github) which gh >/dev/null 2>&1 && gh --version | head -1 || echo "gh: MISSING — brew install gh" ;;
  gitlab) which glab >/dev/null 2>&1 && glab --version | head -1 || echo "glab: MISSING — brew install glab" ;;
esac

# Compound intelligence stack
which graphify >/dev/null 2>&1 && echo "graphify: OK" || echo "graphify: MISSING — run: pipx install graphifyy"
which bun >/dev/null 2>&1 && echo "bun: OK ($(bun --version))" || echo "bun: MISSING — run: curl -fsSL https://bun.sh/install | bash"
node --version 2>/dev/null | grep -q 'v2[2-9]\|v[3-9]' && echo "node: OK ($(node --version))" || echo "node: MISSING or <22 — run: nvm install 22"

# Plugins
grep -q '"claude-mem@thedotmack"' ~/.claude/settings.json 2>/dev/null && echo "claude-mem plugin: OK" || echo "claude-mem plugin: MISSING — run: claude plugins add claude-mem@thedotmack"
grep -q '"superpowers@claude-plugins-official"' ~/.claude/settings.json 2>/dev/null && echo "superpowers plugin: OK" || echo "superpowers plugin: MISSING — run: claude plugins add superpowers@claude-plugins-official"

# Global hooks
grep -q 'hybrid-search/hook.sh' ~/.claude/settings.json 2>/dev/null && echo "hybrid-search hooks: OK" || echo "hybrid-search hooks: MISSING — configure ~/.claude/settings.json per setup guide"
grep -q 'auto-rebuild-graph.sh' ~/.claude/settings.json 2>/dev/null && echo "auto-rebuild hook: OK" || echo "auto-rebuild hook: MISSING — configure ~/.claude/settings.json per setup guide"
grep -q 'crystallize.sh' ~/.claude/settings.json 2>/dev/null && echo "SessionEnd hooks: OK" || echo "SessionEnd hooks: MISSING — configure ~/.claude/settings.json per setup guide"

# knowledge-base skill
test -f ~/.claude/skills/knowledge-base/SKILL.md && echo "knowledge-base skill: OK" || echo "knowledge-base skill: MISSING — install from your skills repository"
```

If any prerequisite is missing, stop and print the install commands. Do NOT proceed until all are available.

---

## Step 2 — Authenticate

Check current auth status:

**GitHub:**
```bash
gh auth status 2>&1
```

**GitLab:**
```bash
glab auth status 2>&1
```

If not authenticated, instruct the user to run the login command themselves (it's interactive):

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

## Step 3 — Capture Working Directory & Detect Prior Init

```bash
# If invoked from inside an existing managed workspace, walk up to its root so we re-init the
# correct directory. If no `.workdir/` (or legacy `.init-workdir/`) marker is found anywhere up
# the tree, fall back to $(pwd) — this is the fresh-init case.
ORIG_PWD=$(pwd)
WORKDIR="$ORIG_PWD"
while [ "$WORKDIR" != "/" ] && [ ! -d "$WORKDIR/.workdir" ] && [ ! -d "$WORKDIR/.init-workdir" ]; do
  WORKDIR=$(dirname "$WORKDIR")
done
if [ "$WORKDIR" = "/" ]; then
  WORKDIR="$ORIG_PWD"   # fresh init at cwd
else
  [ "$WORKDIR" != "$ORIG_PWD" ] && echo "Detected existing workdir: $WORKDIR (invoked from $ORIG_PWD)"
fi
WORKDIR_BASENAME=$(basename "$WORKDIR")
CURRENT_VERSION=$(awk '/^version:/{print $2; exit}' ~/.claude/skills/workdir/SKILL.md)

echo "Workspace:           $WORKDIR"
echo "Skill version:       $CURRENT_VERSION"
```

**Auto-migrate legacy state dir** (`.init-workdir/` → `.workdir/`) if present from a v1
workspace. The directory rename is atomic and preserves the manifest:

```bash
if [ -d "$WORKDIR/.init-workdir" ] && [ ! -d "$WORKDIR/.workdir" ]; then
  mv "$WORKDIR/.init-workdir" "$WORKDIR/.workdir"
  echo "Migrated state dir:  .init-workdir/ → .workdir/ (v1 → v2 layout)"
fi
```

**Read prior init manifest** (informational — per-step probes remain the source of truth):

```bash
MANIFEST="$WORKDIR/.workdir/state.json"
if [ -f "$MANIFEST" ]; then
  PRIOR_VERSION=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["skillVersion"])' "$MANIFEST" 2>/dev/null || echo "")
  PRIOR_AT=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("appliedAt",""))' "$MANIFEST" 2>/dev/null || echo "")
  echo "Prior init:          $PRIOR_VERSION at $PRIOR_AT"
  STATE="UPGRADE"
elif grep -q 'Multi-Repo Workspace' "$WORKDIR/CLAUDE.md" 2>/dev/null; then
  PRIOR_VERSION="legacy"
  echo "Prior init:          legacy (CLAUDE.md present, no manifest)"
  STATE="LEGACY"
else
  PRIOR_VERSION=""
  echo "Prior init:          none (fresh workspace)"
  STATE="NEW"
fi
```

**Print changelog diff** when re-initing at a different version:

```bash
if [ -n "$PRIOR_VERSION" ] && [ "$PRIOR_VERSION" != "$CURRENT_VERSION" ] && [ "$PRIOR_VERSION" != "legacy" ]; then
  echo ""
  echo "Changes since $PRIOR_VERSION → $CURRENT_VERSION:"
  awk -v prior="$PRIOR_VERSION" '
    /^## / && $2 == prior { exit }
    /^## / { active=1 }
    active { print }
  ' ~/.claude/skills/workdir/CHANGELOG.md
elif [ "$PRIOR_VERSION" = "legacy" ]; then
  echo ""
  echo "No version manifest found — every step will probe current state and apply only what's missing."
  echo "See ~/.claude/skills/workdir/CHANGELOG.md for the full version history."
fi
```

**Confirm with the user:**

| State | Prompt | On "no" |
|-------|--------|---------|
| `NEW` | "Initialize workspace at `<WORKDIR>`?" | Abort |
| `UPGRADE` (same version) | "Workspace already at `$CURRENT_VERSION`. Re-run all steps to verify state?" | Skip to Step 15 (summary) |
| `UPGRADE` (older version) | "Upgrade workspace from `$PRIOR_VERSION` → `$CURRENT_VERSION`? Steps will probe current state and apply only what's missing or changed." | Skip to Step 15 (summary) |
| `LEGACY` | "Workspace exists but has no manifest. Run all steps with idempotency probes (existing files preserved) and write the manifest?" | Skip to Step 15 (summary) |

In all "yes" cases, proceed to Step 4. **Each subsequent step probes the workspace itself** —
the manifest is read for the upgrade summary above but is **not** used to skip steps.

---

## Step 4 — Project-Level Gitconfig

**Probe existing config** before prompting:

```bash
EXISTING_NAME=$(git config -f "$WORKDIR/.gitconfig" --get user.name 2>/dev/null || echo "")
EXISTING_EMAIL=$(git config -f "$WORKDIR/.gitconfig" --get user.email 2>/dev/null || echo "")
if [ -n "$EXISTING_NAME" ] && [ -n "$EXISTING_EMAIL" ]; then
  echo "✓ Gitconfig already set: $EXISTING_NAME <$EXISTING_EMAIL>"
  echo "  Skipping prompt (delete $WORKDIR/.gitconfig to re-prompt)"
  NAME="$EXISTING_NAME"
  EMAIL="$EXISTING_EMAIL"
else
  echo "+ Gitconfig missing or incomplete — prompting"
fi
```

If `EXISTING_NAME` and `EXISTING_EMAIL` are set, skip the prompt and reuse them. Otherwise ask:
```
What name should git use for commits in this workspace?
What email address?
```

**Create `<WORKDIR>/.gitconfig`:**

GitHub:
```ini
[user]
    name = <NAME>
    email = <EMAIL>
[credential "https://github.com"]
    helper = !gh auth git-credential
```

GitLab:
```ini
[user]
    name = <NAME>
    email = <EMAIL>
[credential "https://gitlab.com"]
    helper = store
```

**Wire via global gitconfig includeIf.** Check first:
```bash
grep -qF "gitdir:${WORKDIR}" ~/.gitconfig 2>/dev/null && echo "EXISTS" || echo "NEW"
```

If NEW, append to `~/.gitconfig`:
```ini

[includeIf "gitdir:<WORKDIR>/"]
    path = <WORKDIR>/.gitconfig
```

Use the actual absolute path in the written file.

---

## Step 5 — Configure Workspace Ignore Files

Set up ignore files **before** building the graph.

**`.gitignore`** — create or update at `<WORKDIR>/.gitignore`. Add if not present:
```
# Graphify generated output
graphify-out/

# Claude Code project settings
.claude/

# workdir state manifest
.workdir/
```

**`.claudeignore`** — create or update at `<WORKDIR>/.claudeignore`. Add if not present:
```
# Graphify generated output (large JSON/HTML — use GRAPH_REPORT.md instead)
graphify-out/*.html
graphify-out/graph.json
graphify-out/cypher.txt
graphify-out/.graphify_*
```

**`.graphifyignore`** — create or update at `<WORKDIR>/.graphifyignore`. Add the common patterns
(always include for all workspaces):
```
# Test fixtures and snapshots
**/__snapshots__/
**/fixtures/
**/testdata/

# Large data files
*.csv
*.parquet
*.sqlite

# IDE settings
.idea/
.vscode/
*.iml

# Lock files (all stacks)
package-lock.json
yarn.lock
bun.lock
pnpm-lock.yaml
poetry.lock
Pipfile.lock

# Generated/compiled artifacts
*.min.js
*.min.css
*.generated.*
*.class
*.pyc
*.pyo
```

Preserve all existing entries. Do NOT duplicate entries that already exist.

---

## Step 6 — Install Graphify Hook at Workspace Level

```bash
cd "$WORKDIR" && export PATH="$HOME/.local/bin:$PATH" && graphify claude install
```

This writes the PreToolUse hook to `<WORKDIR>/.claude/settings.json` so Glob and Grep calls
made from a parent-level session automatically consult the cross-repo knowledge graph.

If `graphify claude install` fails, manually verify or write the hook to `.claude/settings.json`.

---

## Step 7 — Initialize Knowledge Vault

Create the knowledge vault directory and initialize it using the knowledge-base skill:

```bash
mkdir -p "$WORKDIR/knowledgebase"
```

Then invoke the knowledge-base skill to initialize the vault at `<WORKDIR>/knowledgebase`:

```
/knowledge-base init <WORKDIR>/knowledgebase
```

This creates the vault structure (`.archdesigner/config.json`, `docs/`, etc.) so all architecture documents and diagrams for this workspace have a registered home.

If the vault directory already exists and contains `.archdesigner/config.json`, skip this step.

---

## Step 8 — Copy Coding Standards

Copy the global coding standards into the workspace so they travel with the project and can be customized per-workspace:

```bash
SKILL_STANDARDS=~/.claude/skills/workdir/CODING_STANDARDS.md
if [ -f "$SKILL_STANDARDS" ]; then
  if [ -f "<WORKDIR>/CODING_STANDARDS.md" ]; then
    echo "CODING_STANDARDS.md already exists — skipping (preserved)"
  else
    cp "$SKILL_STANDARDS" "<WORKDIR>/CODING_STANDARDS.md"
    echo "Copied CODING_STANDARDS.md"
  fi
else
  echo "~/.claude/skills/workdir/CODING_STANDARDS.md not found — skipping"
fi
```

If the file already exists (re-initialization), **do not overwrite** — the user may have customized it.

---

## Step 9 — Write Parent CLAUDE.md

Write `<WORKDIR>/CLAUDE.md`. If it already exists and has `## Projects` entries, read those
first and preserve them. Write the new file preserving any `## Projects` @include lines.

```markdown
# <WORKDIR_BASENAME> — Multi-Repo Workspace

Provider: <github|gitlab>
CLI: <gh|glab>

## Projects

<!-- @includes are added automatically when you run /workdir clone -->

## graphify — Structural Intelligence

This workspace has a cross-repo graphify knowledge graph at `graphify-out/`.

### Rules
- Before answering architecture or codebase questions across repos, read `graphify-out/GRAPH_REPORT.md` for god nodes and community structure
- If `graphify-out/wiki/index.md` exists, navigate it instead of reading raw files
- The graph auto-rebuilds on every Write/Edit via the global PostToolUse hook — no manual rebuild needed for small changes
- For per-project deep dives, use the project graph: `<group>/<repo>/graphify-out/GRAPH_REPORT.md`
- Use `/graphify query "question"` for semantic search across all repos
- Use `/graphify path "A" "B"` to find how two concepts connect

### When to Manually Rebuild
- After cloning new repos into the workspace
- After large refactors or batch file operations outside Claude Code
- Run `/graphify . --update` for incremental rebuild (only changed files)

### Token Efficiency
- The cross-repo knowledge graph provides ~70x token reduction vs reading raw files
- Always check `graphify-out/GRAPH_REPORT.md` before doing broad multi-repo searches
- Use `/graphify query` instead of grep for conceptual questions

## claude-mem — Temporal Intelligence

This workspace uses claude-mem for persistent session memory.

### How It Works
- Every session automatically captures tool calls, decisions, bug fixes, and architectural choices
- Observations are stored in `~/.claude-mem/claude-mem.db` with FTS5 full-text search
- Observations decay over time (Ebbinghaus curve, 30-day half-life) but frequently accessed ones stay alive longer
- At session end, observations are promoted through 4 tiers:
  1. **Working memory** — raw tool call observations (auto-captured)
  2. **Episodic** — session-scoped observations with timestamps
  3. **Crystallized** — concept clusters distilled into structured pages at `~/.claude-mem/crystallized/`
  4. **Procedural** — repeated workflows extracted as reusable templates at `~/.claude-mem/procedures/`

### Rules
- Use `/mem-search <query>` to find relevant work from past sessions
- When making architectural decisions, explain the "why" — claude-mem captures it for future sessions
- When fixing bugs, describe the root cause — it becomes searchable knowledge
- Check past session context before re-solving problems that may have been addressed before
- Use `/hybrid-search crystals` to view crystallized knowledge pages
- Use `/hybrid-search procedures` to view extracted workflow recipes

## MEMORY.md — Curated Intelligence

MEMORY.md stores durable, human-curated knowledge that should always be in context.

### What Goes Here (not in claude-mem or graphify)
- User preferences and corrections (`type: feedback`)
- Project context, deadlines, stakeholder info (`type: project`)
- External resource pointers (`type: reference`)
- User role and expertise (`type: user`)

### Memory Routing Protocol
Before saving anything, route to the correct system:

| What to save | Where | Why |
|---|---|---|
| User preferences, corrections, feedback | MEMORY.md | Curated, durable, user-controlled |
| Project context, deadlines, stakeholder info | MEMORY.md | Outlives sessions, needs human curation |
| External resource pointers | MEMORY.md | Stable pointers to external systems |
| Bug fixes, decisions, discoveries | claude-mem (auto-captured) | High-volume temporal stream, auto-indexed |
| Code structure, relationships | graphify (auto-discovered) | Derived from source, always fresh via rebuild hooks |

Before saving to MEMORY.md, check:
1. Does claude-mem already have an observation covering this?
2. Is this derivable from the code? (graphify will discover it)
3. Is this a durable preference or a one-time fact? (one-time → claude-mem; durable → MEMORY.md)

## Knowledge Base

All architecture documents and diagrams for this workspace live in `knowledgebase/`.

### Rules
- Use `/kb document "<topic>"` for architecture docs, decision records, runbooks, and technical notes
- Use `/kb diagram "<topic>"` for architecture diagrams and visual overviews
- Use `/kb create "<topic>"` to generate a document and linked diagram together
- Use `/kb edit <path>` to modify an existing diagram — **never edit diagram JSON directly** (enforces placement constraints, collision checks, and field names)
- Never write standalone Markdown files for architecture or design content — use `/kb` so content is indexed, cross-referenced, and linked
- The vault is at `<WORKDIR>/knowledgebase/` — all `/kb` commands are scoped to this workspace

### When to Use
| Need | Command |
|------|---------|
| Design a new service or component | `/kb create "<name>"` |
| Architecture decision record (ADR) | `/kb document "decision: <topic>"` |
| Debugging runbook | `/kb document "runbook: <topic>"` |
| System overview or sequence diagram | `/kb diagram "<topic>"` |
| Modify an existing diagram | `/kb edit <path> "<what to change>"` |
| Onboarding or operational guide | `/kb document "<topic>"` |

## Coding Standards

This workspace maintains a local copy of coding standards at `CODING_STANDARDS.md`. Read it before writing or reviewing any non-trivial code.

### Rules
- **Before writing non-trivial code:** read `CODING_STANDARDS.md` for naming, SOLID, architecture, testing, security, and error-handling conventions
- **Project instructions override workspace standards:** individual repo `CLAUDE.md` files take precedence over this file, which takes precedence over `CODING_STANDARDS.md`
- **Customizable:** edit `CODING_STANDARDS.md` in this workspace to add project-specific conventions — changes here apply to all repos in this workspace

## Feature & Test Tracking

Every repository in this workspace maintains `Features.md` and `test-cases/` at its root. These are created automatically when a repo is cloned via `/workdir clone`.

### Features.md — Source of Truth for Features

`Features.md` is the canonical catalogue of every user-facing feature and internal sub-system. It drives test scope, onboarding, and scope reviews.

#### Rules
- **Keep it in sync with the code.** Whenever you add, remove, enhance, rename, or otherwise change a feature, update `Features.md` in the same change set — never in a follow-up.
- **Scope that triggers an update:** new/removed/renamed modules, components, APIs, CLI commands, data models, configuration options, integrations, or significant internal sub-systems.
- Adding → add a bullet under the right section with a one-to-two-line description and the file path.
- Removing → delete the bullet. No tombstones.
- Enhancing → edit the existing bullet. If a genuinely new capability, add a sub-bullet.
- **Legend discipline:** `✅` user-observable, `⚙️` internal subsystem, `?` inferred/unverified. Promote `?` once confirmed; never leave a `?` you introduced.
- **No silent drift.** Any PR that touches source files and leaves `Features.md` untouched is incomplete.
- **Cross-check on every session.** Before claiming a feature task is done, re-read the affected section of `Features.md` and confirm it still describes reality.

### test-cases/ — Source of Truth for Test Scenarios

`test-cases/` holds the human-readable catalogue of every scenario worth covering, one file per top-level feature bucket, mirroring `Features.md`'s section numbering. It is the scope contract between features and tests.

#### Rules
- **Keep it in sync with Features.md.** When a feature is added, removed, renamed, or enhanced, update both `Features.md` AND the owning file under `test-cases/` in the same change set.
- **Add a case** using the next free number in the matching section. Start new cases at status ❌.
- **Never renumber existing IDs.** If a case is deleted, leave its number unused — new cases continue past it.
- **Flip the status marker** (❌ → ✅ / 🟡 / 🧪) in the same commit as the test that covers it. Use 🚫 with a one-line reason only when consciously out of scope.
- **Cross-reference tests by ID.** Test names or comments should include the case ID so grep finds both directions.
- **Prose only.** Actual test files live in the test framework directories. `test-cases/` is scenario descriptions, not code.

## UI/UX Design — Design Intelligence

The `ui-ux-pro-max` skill is installed in this workspace via `uipro-cli`. It provides design
system generation, UI style/color/font/UX recommendations, and frontend code generation across
15 stacks.

### Rules
- **Use this skill for all UI/UX work** — new designs, design audits, design edits, component
  styling, color/font/layout decisions, accessibility reviews, and frontend code generation
- The skill auto-activates when the request involves design, styling, layout, components, or
  visual decisions — let it handle the design reasoning rather than freelancing
- For UI implementation work, prefer the skill's stack-aware code generation over ad-hoc
  styling — it bakes in spacing, color tokens, accessibility, and responsive layout
- Re-sync to the latest version with `uipro update`; reinstall with `uipro init --ai claude`

### When to Use
| Need | Action |
|------|--------|
| New design system for a service/app | Invoke ui-ux-pro-max with project context |
| Audit existing UI for design issues | Invoke ui-ux-pro-max with the component or page |
| Edit/improve a component's styling | Invoke ui-ux-pro-max with the current code |
| Pick palette / fonts / UI style | Invoke ui-ux-pro-max with product category |
| Generate UI code in a target stack | Invoke ui-ux-pro-max with the design + stack |

### Superpowers Integration

ui-ux-pro-max does **not** auto-pair with superpowers skills — they're independent skills loaded
into the same context. Whenever a superpowers workflow touches UI, invoke ui-ux-pro-max
alongside the workflow skill:

| Superpowers step | How ui-ux-pro-max plugs in |
|---|---|
| `brainstorming` for a UI feature | Pull style/palette/layout direction from ui-ux-pro-max before the brainstorm crystallises |
| `writing-plans` for UI work | ui-ux-pro-max informs component breakdown, design tokens, and stack-specific code targets |
| `executing-plans` / `subagent-driven-development` | Name the design constraints in the subagent prompt so the dispatched agent invokes ui-ux-pro-max alongside its primary skill (compound-dispatch will not surface this on its own) |
| `systematic-debugging` for a UI bug | Bring in ui-ux-pro-max for visual/layout root-cause hypotheses |
| `requesting-code-review` / `receiving-code-review` on UI code | Use ui-ux-pro-max as a second opinion on accessibility, spacing, color contrast, responsive behaviour |

## superpowers — Workflow Intelligence

All significant code changes in this workspace go through superpowers skills. Skipping them bypasses compound intelligence context.

### Development Workflow

| Situation | Skills to invoke |
|-----------|-----------------|
| Starting a new feature | `superpowers:brainstorming` → `superpowers:writing-plans` → `superpowers:test-driven-development` |
| Executing a written plan | `superpowers:executing-plans` |
| Debugging any failure | `superpowers:systematic-debugging` |
| Completing / about to claim done | `superpowers:verification-before-completion` |
| Requesting code review | `superpowers:requesting-code-review` |
| Receiving code review feedback | `superpowers:receiving-code-review` |
| UI/UX work inside any workflow | Pair the workflow skill with `ui-ux-pro-max` (e.g. brainstorming + ui-ux-pro-max for new components, executing-plans + ui-ux-pro-max for UI implementation tasks) — see UI/UX Design § Superpowers Integration |

### Compound-Dispatch Integration

Every superpowers skill that dispatches subagents routes through compound-dispatch — subagents receive prior knowledge from all three memory systems automatically.

### Rules
- **Before any subagent dispatch** — including those launched by superpowers skills — run `/compound-dispatch` to inject graph context, temporal memory, and curated preferences into the subagent prompt
- superpowers brainstorming: compound-dispatch injects structural graph context so brainstorms are aware of existing architecture
- superpowers TDD: compound-dispatch injects past test patterns and prior bug fixes
- superpowers debugging: compound-dispatch injects prior observations about the failing area
- superpowers code-review: compound-dispatch injects coding preferences from MEMORY.md; findings are saved back to MEMORY.md after the review

## Compound Intelligence

graphify (structural) + claude-mem (temporal) + MEMORY.md (curated) = unified intelligence.

### How It Works Together
- **On file read**: The PreToolUse hook auto-injects graph neighbors + relevant MEMORY.md entries (session-deduped, token-budgeted)
- **On file write/edit**: The PostToolUse hook auto-rebuilds the cross-repo graph incrementally (rate-limited to 30s)
- **On subagent dispatch** (including superpowers skills): `/compound-dispatch` enriches each subagent with "Prior Knowledge" from all 3 systems via `gather-context.py`
- **On session end**: Observations crystallize into knowledge pages; repeated workflows become procedures
- **On observation access**: Relevance counter increments, extending the observation's decay half-life
- **Contradiction detection**: New observations are checked against similar older ones; conflicts are flagged

### Available Commands
| Command | What it does |
|---------|-------------|
| `/graphify .` | Build/rebuild cross-repo knowledge graph |
| `/graphify . --update` | Incremental rebuild (changed files only) |
| `/graphify query "question"` | Semantic search across all repos |
| `/hybrid-search "topic"` | Fused search across temporal + structural |
| `/hybrid-search contradictions` | View detected observation conflicts |
| `/hybrid-search crystals` | View crystallized knowledge pages |
| `/hybrid-search procedures` | View extracted workflow recipes |
| `/mem-search "query"` | Search claude-mem observation history |
| `/compound-dispatch` | Enrich subagent prompt with unified context |
| `/workdir clone <url>` | Clone a repo and register it in this workspace |

## Git Configuration

Provider: <github|gitlab>
Identity: `<NAME> <<EMAIL>>`
Config file: `<WORKDIR>/.gitconfig`
Applied to all repos via `~/.gitconfig` includeIf.
```

**Important:** When the file already exists:
- Preserve ALL existing content, especially `## Projects` @include lines
- Replace any existing graphify/claude-mem/compound sections with the version above
- Do NOT duplicate sections — update in place

---

## Step 10 — Start Claude-Mem Worker

```bash
source ~/.nvm/nvm.sh && nvm use 22 2>/dev/null
export PATH="$HOME/.bun/bin:$PATH"
npx claude-mem status 2>&1 || npx claude-mem start 2>&1
```

---

## Step 11 — Build Initial Knowledge Graph (Optional)

If graphify is available and repos are already present, ask:
> "Would you like to build the initial cross-repo knowledge graph now? This analyzes all cloned repos and may take a few minutes for large codebases."

If yes:
```bash
cd "$WORKDIR" && export PATH="$HOME/.local/bin:$PATH" && graphify . --update
```

---

## Step 12 — Install UI/UX Pro Max Skill

Provides design intelligence for all UI/UX work in this workspace: 67 UI styles, 161 color
palettes, 57 font pairings, 99 UX guidelines, and code generation across 15 frontend stacks.
Distributed via the `uipro-cli` npm package and installed into Claude Code as a skill.

```bash
export PATH="$HOME/.bun/bin:$PATH"

# Install the CLI globally if missing
if ! command -v uipro >/dev/null 2>&1; then
  echo "uipro-cli: MISSING — installing globally via npm"
  npm install -g uipro-cli
fi

# Idempotent: re-running re-syncs the skill to the latest version
cd "$WORKDIR" && uipro init --ai claude
```

If `npm` is missing, instruct the user to install Node 22+ and re-run `/workdir init <provider>`.
If `uipro init --ai claude` fails (network, registry), surface the error and continue — the rest
of the workspace setup is unaffected.

Reference: https://github.com/nextlevelbuilder/ui-ux-pro-max-skill

---

## Step 13 — Bootstrap MEMORY.md Seeds

MEMORY.md is per-workspace, per-machine — it lives at
`~/.claude/projects/<encoded-workdir>/memory/MEMORY.md`, not inside the workspace tree, so a
fresh machine running `/workdir init` starts with an empty MEMORY.md. To make portable,
durable feedback travel with the skill, the skill ships memory seeds in
`~/.claude/skills/workdir/memory-seeds/`. This step copies them into the workspace's
memory dir on first init (idempotent — preserves existing files).

```bash
SEEDS_DIR=~/.claude/skills/workdir/memory-seeds
[ -d "$SEEDS_DIR" ] || { echo "No memory seeds shipped — skipping"; exit 0; }

MEMORY_DIR=$(python3 -c "
import os, re
workdir = os.path.realpath('$WORKDIR')
# Claude Code encodes project paths by replacing every non-alphanumeric character (slashes,
# spaces, dots, underscores, etc.) with '-'. Must match exactly or seeds land in a sibling
# directory that the running session never reads.
encoded = re.sub(r'[^A-Za-z0-9]', '-', workdir)
print(os.path.expanduser(f'~/.claude/projects/{encoded}/memory'))
")

mkdir -p "$MEMORY_DIR"
touch "$MEMORY_DIR/MEMORY.md"

for seed in "$SEEDS_DIR"/*.md; do
  [ -f "$seed" ] || continue
  basename=$(basename "$seed")
  if [ -f "$MEMORY_DIR/$basename" ]; then
    echo "  $basename: EXISTS (preserved)"
    continue
  fi
  cp "$seed" "$MEMORY_DIR/$basename"
  echo "  $basename: SEEDED"

  # Add to MEMORY.md index if not already there
  name=$(awk -F': ' '/^name:/ {print $2; exit}' "$seed")
  desc=$(awk -F': ' '/^description:/ {print $2; exit}' "$seed")
  index_line="- [$name]($basename) — $desc"
  if ! grep -qF "($basename)" "$MEMORY_DIR/MEMORY.md" 2>/dev/null; then
    echo "$index_line" >> "$MEMORY_DIR/MEMORY.md"
  fi
done
```

Existing seed files already present in the workspace memory dir are **never** overwritten —
the user may have edited them. New seeds added in future skill versions will be picked up on
the next `/workdir update` run.

---

## Step 14 — Persist Init Manifest

Record this run for future re-init diffing. The manifest is **informational only** — re-init
relies on per-step probes for correctness, never on the manifest's `appliedSteps` list.

```bash
mkdir -p "$WORKDIR/.workdir"
APPLIED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)

python3 - "$WORKDIR/.workdir/state.json" "$CURRENT_VERSION" "$APPLIED_AT" <<'PY'
import json, os, sys
path, version, applied_at = sys.argv[1], sys.argv[2], sys.argv[3]
state = {"skillVersion": version, "appliedAt": applied_at, "history": []}
if os.path.exists(path):
    try:
        prev = json.load(open(path))
        state["history"] = prev.get("history", [])
        if prev.get("skillVersion"):
            state["history"].append({
                "version": prev["skillVersion"],
                "appliedAt": prev.get("appliedAt", ""),
            })
    except Exception:
        pass
with open(path, "w") as fh:
    json.dump(state, fh, indent=2)
PY

echo "Manifest written: $WORKDIR/.workdir/state.json (version $CURRENT_VERSION)"
```

The manifest schema:

```json
{
  "skillVersion": "1.2.0",
  "appliedAt": "2026-05-04T10:35:00Z",
  "history": [
    { "version": "1.0.0", "appliedAt": "2026-04-21T16:20:00Z" },
    { "version": "1.1.0", "appliedAt": "2026-05-04T10:18:00Z" }
  ]
}
```

The schema is intentionally minimal — `skillVersion` and `appliedAt` are the only fields the
re-init logic reads. `history` is for the human reading the file.

---

## Step 15 — Summary

```
Workspace initialized: <WORKDIR>

  Provider:    <github|gitlab>
  CLI:         <gh|glab>  (authenticated ✓)
  Identity:    <NAME> <<EMAIL>>
  Gitconfig:   <WORKDIR>/.gitconfig
               Wired via ~/.gitconfig includeIf for all repos under this directory

  CLAUDE.md:   <WORKDIR>/CLAUDE.md  (compound intelligence hub)
  MEMORY.md:   ~/.claude/projects/<encoded-workdir>/memory/MEMORY.md  (auto-created on first save)
  Manifest:    <WORKDIR>/.workdir/state.json  (skill version $CURRENT_VERSION, history of prior runs)

  Compound Intelligence Stack:
    graphify (structural)
      Hook:    <WORKDIR>/.claude/settings.json (PreToolUse Glob|Grep)
      Auto:    Cross-repo graph rebuilds on Write/Edit/Bash (PostToolUse hook, 30s rate limit)
      Graph:   <WORKDIR>/graphify-out/ (run /graphify . to build)

    claude-mem (temporal)
      Plugin:  claude-mem@thedotmack (global)
      Worker:  http://localhost:37777
      Pipeline: raw → episodic → crystallized → procedural (auto on session end)

    MEMORY.md (curated)
      Routing: Preferences → MEMORY.md | Facts → claude-mem | Structure → graphify

    hybrid-search (fused retrieval)
      Hook:    PreToolUse Read — auto-injects graph + memory context
      Query:   /hybrid-search "topic"

    compound-dispatch (subagent enrichment)
      Script:  ~/.claude/skills/compound-dispatch/gather-context.py
      Auto:    Subagents get "Prior Knowledge" from all 3 systems

    superpowers (workflow intelligence)
      Plugin:  superpowers@claude-plugins-official (global)
      Rules:   brainstorming → writing-plans → TDD for features; systematic-debugging for bugs

    knowledge base (documentation vault)
      Vault:   <WORKDIR>/knowledgebase/
      Skill:   knowledge-base (local skill)
      Use:     /kb create|document|diagram|edit "<topic|path>" for all docs and diagrams

    ui-ux-pro-max (design intelligence)
      CLI:     uipro-cli (global npm)
      Skill:   installed via `uipro init --ai claude`
      Use:     auto-activates for design system generation, UI audits, and frontend code

Next steps:
  Clone a repo:        /workdir clone <url>
  Clone with group:    /workdir clone <url> --group <name>
  Build graph:         /graphify .
  Search memory:       /mem-search "query"
  Fused search:        /hybrid-search "topic"
  Enrich subagents:    /compound-dispatch
  New document:        /kb document "<topic>"
  New diagram:         /kb diagram "<topic>"
  Doc + diagram:       /kb create "<topic>"
  Edit diagram:        /kb edit <path> "<change>"
```
