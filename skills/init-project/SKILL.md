---
name: init-project
description: >
  Use this skill when the user asks to initialize a project, set up graphify and claude-mem,
  bootstrap project intelligence, or says things like "init this project", "set up memory",
  "initialize graphify", "set up project tools", "init", "bootstrap project".
  This skill configures the full compound intelligence stack — graphify (structural),
  claude-mem (temporal), MEMORY.md (curated), hybrid-search (fused retrieval),
  compound-dispatch (subagent enrichment), and superpowers (workflow intelligence) —
  for the current project.
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash]
version: 2.0.0
---

# Initialize Project: Compound Intelligence Stack

Set up the full compound intelligence stack for the current project. This makes Claude Code structurally aware of the codebase, preserves session memory across conversations, and ensures subagents start informed.

## What This Skill Does

1. Verifies all global prerequisites (graphify, claude-mem, superpowers, hybrid-search hooks)
2. Installs graphify's Claude Code integration for this project
3. Writes enhanced CLAUDE.md with all three memory systems and routing protocol
4. Starts the claude-mem worker
5. Optionally builds the initial knowledge graph

## Prerequisites

These must be installed **globally** before running this skill:

| Tool | Install | Verify |
|------|---------|--------|
| graphify CLI | `pipx install graphifyy` | `graphify --version` |
| claude-mem plugin | `claude plugins add claude-mem@thedotmack` | `claude plugins list \| grep claude-mem` |
| superpowers plugin | `claude plugins add superpowers@claude-plugins-official` | `claude plugins list \| grep superpowers` |
| bun runtime | `curl -fsSL https://bun.sh/install \| bash` | `bun --version` |
| Node.js 22+ | `nvm install 22` | `node --version` |

Global hooks and skills must be configured per the setup guide (`~/.claude/settings.json` and `~/.claude/CLAUDE.md`).

## Step 1 — Verify Prerequisites

Run these checks. If any fail, tell the user what's missing and how to install it.

```bash
export PATH="$HOME/.local/bin:$HOME/.bun/bin:$PATH"

# Core tools
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
```

If any prerequisite is missing, stop and print the install commands. Do NOT proceed until all are available.

## Step 2 — Install Graphify for This Project

Run the graphify Claude Code installer. This registers the PreToolUse hook in `.claude/settings.json` for this project.

```bash
export PATH="$HOME/.local/bin:$PATH"
graphify claude install
```

This will:
- Add a `## graphify` section to CLAUDE.md (basic version — we'll enhance it in Step 3)
- Register a `PreToolUse` hook in `.claude/settings.json` that checks for the knowledge graph before file searches

If `.claude/settings.json` already has the graphify hook, skip this step.

## Step 3 — Update Ignore Files

Ensure generated artifacts are excluded from version control and Claude Code context.

### .gitignore

Read the project's `.gitignore` (create if it doesn't exist). Add these entries if not already present:

```
# Graphify generated output
graphify-out/

# Claude Code project settings
.claude/
```

### .claudeignore

Read the project's `.claudeignore` (create if it doesn't exist). Add these entries if not already present:

```
# Graphify generated output (large JSON/HTML — use GRAPH_REPORT.md instead)
graphify-out/*.html
graphify-out/graph.json
graphify-out/cypher.txt
graphify-out/.graphify_*
```

**Why not ignore all of `graphify-out/`?** Claude needs access to `GRAPH_REPORT.md` and `wiki/` for architecture questions. Only the large generated artifacts (HTML visualization, raw JSON graph, Neo4j export, internal detection files) should be excluded from Claude's context.

### .graphifyignore

Graphify supports `.graphifyignore` (gitignore syntax) to control what enters the knowledge graph. It already skips common noise dirs (`node_modules`, `dist`, `build`, `__pycache__`, `.venv`, etc.) by default.

Read the project's `.graphifyignore` (create if it doesn't exist). Add project-specific entries for directories that would add noise to the graph.

**Detect project type** by checking for marker files, then apply the relevant patterns:

#### Common (always include)
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
```

#### JavaScript/TypeScript (if `package.json` exists)
```
# Generated / vendored
*.min.js
*.min.css
*.generated.*

# Lock files
package-lock.json
yarn.lock
bun.lock
pnpm-lock.yaml
```

#### Java / Spring Boot (if `pom.xml` or `build.gradle` exists)
```
# Compiled output (target/ and build/ already skipped by graphify default)
*.jar
*.war
*.ear
*.class

# Gradle
.gradle/
gradle/wrapper/

# Maven wrapper
.mvn/wrapper/

# Spring Boot
*.log
logs/

# Test reports (generated, no structural value)
**/surefire-reports/
**/failsafe-reports/
**/test-results/
```

#### DevOps / Infrastructure (if `*.tf`, `Dockerfile`, `docker-compose.*`, `ansible.cfg`, `helmfile.*`, or `kubernetes/` exists)
```
# Terraform
.terraform/
*.tfstate
*.tfstate.backup
*.tfplan
.terraform.lock.hcl

# Ansible
*.retry

# Helm
**/charts/*.tgz

# Kubernetes generated manifests
**/rendered/
**/generated-manifests/

# CI/CD artifacts
.github/actions/*/dist/

# Vault / secrets (should never enter graph)
**/vault-secrets/
*.enc
*.sealed
```

#### Python (if `pyproject.toml`, `setup.py`, or `requirements.txt` exists)
```
# Lock files
poetry.lock
Pipfile.lock

# Generated
*.pyc
*.pyo
```

**Adapt to the project** — inspect the directory structure and only include patterns relevant to the detected project type. A Java Spring Boot project doesn't need JS patterns and vice versa. If the project is multi-type (e.g., Spring Boot backend with a React frontend), include both sets.

**Note:** Claude-mem does not have an ignore file — it captures observations from Claude's tool calls, not from file scanning, so there is nothing to exclude at the file level.

**Important:**
- Preserve ALL existing entries in all ignore files
- Do NOT duplicate entries that already exist
- Add a blank line before new sections if the file doesn't end with one

## Step 4 — Write Enhanced CLAUDE.md Instructions

After graphify writes its basic section, **replace** the entire `## graphify` section AND append new sections with the enhanced version below.

Read the existing CLAUDE.md first. Preserve everything that is NOT the graphify/claude-mem/compound-intelligence sections. Then replace/append so the file contains these sections (adapt the content to the project — replace placeholder descriptions with actual project context):

```markdown
## graphify — Structural Intelligence

This project has a graphify knowledge graph at `graphify-out/`.

### Rules
- Before answering architecture or codebase questions, read `graphify-out/GRAPH_REPORT.md` for god nodes and community structure
- If `graphify-out/wiki/index.md` exists, navigate it instead of reading raw files
- The graph auto-rebuilds on every Write/Edit via the global PostToolUse hook — no manual rebuild needed for small changes
- Use `/graphify query "question"` for semantic search across the codebase
- Use `/graphify path "A" "B"` to find how two concepts connect

### When to Manually Rebuild
- After large refactors or batch file operations outside Claude Code
- After adding new documentation or design docs
- Run `/graphify . --update` for incremental rebuild (only changed files)

### Token Efficiency
- The knowledge graph provides ~70x token reduction vs reading raw files
- Always check `graphify-out/GRAPH_REPORT.md` before doing broad file searches
- Use `/graphify query` instead of grep for conceptual questions

## claude-mem — Temporal Intelligence

This project uses claude-mem for persistent session memory.

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

## Compound Intelligence

graphify (structural) + claude-mem (temporal) + MEMORY.md (curated) = unified intelligence.

### How It Works Together
- **On file read**: The PreToolUse hook auto-injects graph neighbors + relevant MEMORY.md entries (session-deduped, token-budgeted)
- **On file write/edit**: The PostToolUse hook auto-rebuilds the graph incrementally (rate-limited to 30s)
- **On subagent dispatch**: compound-dispatch enriches each subagent with "Prior Knowledge" from all 3 systems via `gather-context.py`
- **On session end**: Observations crystallize into knowledge pages; repeated workflows become procedures
- **On observation access**: Relevance counter increments, extending the observation's decay half-life
- **Contradiction detection**: New observations are checked against similar older ones; conflicts are flagged

### Available Commands
| Command | What it does |
|---------|-------------|
| `/graphify .` | Build/rebuild knowledge graph |
| `/graphify . --update` | Incremental rebuild (changed files only) |
| `/graphify query "question"` | Semantic search across the codebase |
| `/hybrid-search "topic"` | Fused search across temporal + structural |
| `/hybrid-search contradictions` | View detected observation conflicts |
| `/hybrid-search crystals` | View crystallized knowledge pages |
| `/hybrid-search procedures` | View extracted workflow recipes |
| `/mem-search "query"` | Search claude-mem observation history |
| `/compound-dispatch` | Enrich subagent prompt with unified context |
```

**Important:** When writing to CLAUDE.md:
- Preserve ALL existing content (project goal, behavior rules, other sections)
- Replace the basic `## graphify` section that `graphify claude install` wrote with the enhanced version above
- Add all new sections if they don't exist
- Do NOT duplicate sections — if they already exist, update them in place

## Step 5 — Start Claude-Mem Worker

Ensure the claude-mem worker is running:

```bash
source ~/.nvm/nvm.sh && nvm use 22 2>/dev/null
export PATH="$HOME/.bun/bin:$PATH"
npx claude-mem status 2>&1 || npx claude-mem start 2>&1
```

## Step 6 — Build Initial Knowledge Graph (Optional)

Ask the user: "Would you like me to build the initial knowledge graph now? This will analyze your codebase and create the graph at `graphify-out/`. It may take a few minutes for large projects."

If yes, invoke the `/graphify` skill on the current directory:
```
/graphify .
```

If no, tell the user they can run `/graphify .` anytime to build it.

## Step 7 — Summary

Print a completion summary:

```
Project initialized with compound intelligence:

  Graphify (structural)
    Hook:      .claude/settings.json (PreToolUse on Glob|Grep)
    Auto:      Graph rebuilds on Write/Edit/Bash (PostToolUse hook, 30s rate limit)
    Config:    CLAUDE.md (graphify section)
    Graph:     graphify-out/ (run /graphify . to build)
    Query:     /graphify query "question"

  Claude-Mem (temporal)
    Plugin:    claude-mem@thedotmack (global)
    Worker:    http://localhost:37777
    Pipeline:  raw → episodic → crystallized → procedural (auto on session end)
    Search:    /mem-search "query"

  MEMORY.md (curated)
    Location:  project memory/ directory
    Routing:   Preferences → MEMORY.md | Facts → claude-mem | Structure → graphify

  Hybrid Search (fused retrieval)
    Hook:      PreToolUse Read — auto-injects graph + memory context
    Query:     /hybrid-search "topic"
    Decay:     Ebbinghaus curve, 30-day half-life, extended by access

  Compound Dispatch (subagent enrichment)
    Script:    ~/.claude/skills/compound-dispatch/gather-context.py
    Auto:      Subagents get "Prior Knowledge" from all 3 systems

  Superpowers (workflow intelligence)
    Plugin:    superpowers@claude-plugins-official (global)
    Skills:    brainstorming, TDD, debugging, planning, code review, SDD
    Integration: Each skill wired into compound intelligence layer

Next steps:
  1. Run /graphify . to build the knowledge graph (if not done)
  2. Start coding — claude-mem captures automatically, graph rebuilds automatically
  3. Use /hybrid-search to query across all memory systems at once
  4. Use /compound-dispatch when dispatching subagents for enriched context
```
