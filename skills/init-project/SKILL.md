---
name: init-project
description: >
  Use this skill when the user asks to initialize a project, set up graphify and claude-mem,
  bootstrap project intelligence, or says things like "init this project", "set up memory",
  "initialize graphify", "set up project tools", "init", "bootstrap project".
  This skill configures both graphify (structural intelligence) and claude-mem (temporal intelligence)
  for the current project, adds CLAUDE.md instructions, and optionally builds the initial knowledge graph.
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash]
version: 1.0.0
---

# Initialize Project: Graphify + Claude-Mem

Set up both graphify (structural intelligence) and claude-mem (temporal intelligence) for the current project. This makes Claude Code aware of codebase structure across sessions and preserves session memory.

## What This Skill Does

1. Installs graphify's Claude Code integration into the project (hook + CLAUDE.md section)
2. Verifies claude-mem plugin is active globally
3. Adds comprehensive CLAUDE.md instructions for using both tools synergistically
4. Optionally builds the initial knowledge graph

## Prerequisites

These must be installed globally before running this skill:
- `graphify` CLI (`pipx install graphifyy`)
- `claude-mem` plugin (`npx claude-mem install --ide claude-code`)
- `bun` runtime (`curl -fsSL https://bun.sh/install | bash`)

## Step 1 — Verify Prerequisites

Run these checks. If any fail, tell the user what's missing and how to install it.

```bash
# Check graphify
export PATH="$HOME/.local/bin:$PATH"
which graphify >/dev/null 2>&1 && echo "graphify: OK ($(graphify --help | head -1))" || echo "graphify: MISSING — run: pipx install graphifyy"

# Check claude-mem plugin
if grep -q '"claude-mem@thedotmack"' ~/.claude/settings.json 2>/dev/null; then
  echo "claude-mem: OK (plugin enabled)"
else
  echo "claude-mem: MISSING — run: npx claude-mem install --ide claude-code"
fi

# Check bun
export PATH="$HOME/.bun/bin:$PATH"
which bun >/dev/null 2>&1 && echo "bun: OK ($(bun --version))" || echo "bun: MISSING — run: curl -fsSL https://bun.sh/install | bash"
```

If any prerequisite is missing, stop and print the install commands. Do NOT proceed until all three are available.

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

## Step 3 — Write Enhanced CLAUDE.md Instructions

After graphify writes its basic section, **replace** the entire `## graphify` section AND append a new `## claude-mem` section with the enhanced version below.

Read the existing CLAUDE.md first. Preserve everything that is NOT the graphify/claude-mem sections. Then replace/append so the file contains these sections (adapt the content to the project — replace placeholder descriptions with actual project context):

```markdown
## graphify — Structural Intelligence

This project has a graphify knowledge graph at `graphify-out/`.

### Rules
- Before answering architecture or codebase questions, read `graphify-out/GRAPH_REPORT.md` for god nodes and community structure
- If `graphify-out/wiki/index.md` exists, navigate it instead of reading raw files
- After modifying code files, run: `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` to keep the graph current
- Use `/graphify query "question"` for semantic search across the codebase
- Use `/graphify path "A" "B"` to find how two concepts connect

### When to Rebuild
- After significant code changes (new modules, refactors, API changes)
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
- Observations are compressed and stored in `~/.claude-mem/claude-mem.db`
- Future sessions get relevant context injected automatically

### Rules
- Use `/mem-search <query>` to find relevant work from past sessions
- When making architectural decisions, explain the "why" — claude-mem captures it for future sessions
- When fixing bugs, describe the root cause — it becomes searchable knowledge
- Check past session context before re-solving problems that may have been addressed before

### Available Commands
- `/mem-search "query"` — Search past observations across all sessions
- Memory web viewer: http://localhost:37777

## Compound Intelligence Loop

graphify and claude-mem work together:
1. **graphify** provides STRUCTURAL intelligence — what exists, how things relate, cross-domain connections
2. **claude-mem** provides TEMPORAL intelligence — what was done, why decisions were made, session history
3. **Feedback loop**: claude-mem captures graphify discoveries → future sessions get past graph insights injected → no need to re-query for things already learned
```

**Important:** When writing to CLAUDE.md:
- Preserve ALL existing content (project goal, behavior rules, other sections)
- Replace the basic `## graphify` section that `graphify claude install` wrote with the enhanced version above
- Add the `## claude-mem` and `## Compound Intelligence Loop` sections if they don't exist
- Do NOT duplicate sections — if they already exist, update them in place

## Step 4 — Start Claude-Mem Worker

Ensure the claude-mem worker is running:

```bash
source ~/.nvm/nvm.sh && nvm use 22 2>/dev/null
export PATH="$HOME/.bun/bin:$PATH"
npx claude-mem status 2>&1 || npx claude-mem start 2>&1
```

## Step 5 — Build Initial Knowledge Graph (Optional)

Ask the user: "Would you like me to build the initial knowledge graph now? This will analyze your codebase and create the graph at `graphify-out/`. It may take a few minutes for large projects."

If yes, invoke the `/graphify` skill on the current directory:
```
/graphify .
```

If no, tell the user they can run `/graphify .` anytime to build it.

## Step 6 — Summary

Print a completion summary:

```
Project initialized with compound intelligence:

  Graphify (structural)
    Hook:    .claude/settings.json (PreToolUse on Glob|Grep)
    Config:  CLAUDE.md (graphify section)
    Graph:   graphify-out/ (run /graphify . to build)
    Query:   /graphify query "question"

  Claude-Mem (temporal)
    Plugin:  ~/.claude/plugins (global, auto-active)
    Config:  CLAUDE.md (claude-mem section)
    Worker:  http://localhost:37777
    Search:  /mem-search "query"

  Compound Loop
    Structure feeds Memory feeds better Queries feeds richer Memory

Next steps:
  1. Run /graphify . to build the knowledge graph (if not done)
  2. Start coding — claude-mem captures automatically
  3. Use /mem-search to query past session insights
  4. Use /graphify query to search the knowledge graph
```
