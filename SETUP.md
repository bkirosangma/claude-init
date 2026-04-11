# Claude Code Compound Intelligence — Setup Guide

Replicate the full compound intelligence stack on a new system. Everything needed is included in this `claude-setup/` directory.

**Last updated:** 2026-04-12
**Source system:** macOS Darwin 25.3.0, Claude Code with Opus 4.6

---

## Directory Structure

```
claude-setup/
├── SETUP.md                              ← You are here
├── REASONING.md                          ← Design explanations for every component
└── skills/                               ← All skill files, ready to copy
    ├── graphify/SKILL.md                 ← Knowledge graph orchestration (53KB)
    ├── hybrid-search/                    ← Core: fused search + hooks + pipeline
    │   ├── SKILL.md                      ← RRF-fused search skill
    │   ├── hook.sh                       ← PreToolUse Read: context injection
    │   ├── auto-rebuild-graph.sh         ← PostToolUse Write/Edit/Bash: graph rebuild
    │   ├── bump-relevance.sh             ← PostToolUse: decay reinforcement
    │   ├── contradiction-check.sh        ← PostToolUse: conflict detection wrapper
    │   ├── contradiction_check.py        ← Conflict detection logic
    │   ├── decay.py                      ← Ebbinghaus confidence decay scoring
    │   ├── crystallize.sh                ← SessionEnd: Tier 2→3 wrapper
    │   ├── crystallize_impl.py           ← Tier 2→3 knowledge distillation
    │   └── proceduralize.py              ← Tier 3→4 workflow extraction
    ├── compound-dispatch/                ← Unified context for subagents
    │   ├── SKILL.md                      ← Enrichment skill instructions
    │   └── gather-context.py             ← Queries all 3 memory systems
    └── init-project/SKILL.md             ← One-command per-project setup
```

---

## Phase 1: Prerequisites

Install these globally before anything else.

| Tool | Install Command | Purpose |
|------|----------------|---------|
| Claude Code CLI | [claude.ai/download](https://claude.ai/download) | The AI coding assistant |
| Node.js 22+ | `nvm install 22` or [nodejs.org](https://nodejs.org) | Required by claude-mem |
| Bun | `curl -fsSL https://bun.sh/install \| bash` | Required by claude-mem worker |
| Python 3.12+ | System or `pyenv install 3.12` | Required by graphify |
| pipx | `python3 -m pip install pipx && pipx ensurepath` | Isolated Python tool installs |
| graphify | `pipx install graphifyy` | Structural intelligence (knowledge graphs) |

Verify after install:
```bash
graphify --version          # 0.4.1+
node --version              # v22+
bun --version               # 1.0+
python3 --version           # 3.12+
```

Note your graphify Python path (needed later):
```bash
head -1 $(which graphify)
# Example output: #!/Users/YOU/.local/pipx/venvs/graphifyy/bin/python
```

---

## Phase 2: Install Claude Code Plugins

### 2.1 Claude-Mem — Temporal Intelligence

```bash
claude plugins add claude-mem@thedotmack
```

This installs from the thedotmack GitHub marketplace. It:
- Auto-captures observations from every tool call (bugs, decisions, features, etc.)
- Stores in SQLite with FTS5 full-text search at `~/.claude-mem/claude-mem.db`
- Runs a worker service on port 37777 for session context injection
- Provides MCP tools: `search`, `get_observations`, `timeline`, `smart_search`, `smart_outline`

### 2.2 Superpowers — Workflow Intelligence

```bash
claude plugins add superpowers@claude-plugins-official
```

Superpowers provides structured workflow skills that integrate with compound intelligence:

| Skill | Trigger | Compound Intelligence Integration |
|-------|---------|-----------------------------------|
| `brainstorming` | Before creative work | Uses graphify community context to explore existing patterns |
| `writing-plans` | Multi-step tasks | Queries claude-mem for past lessons learned on similar features |
| `executing-plans` | Running implementation plans | Each step enriched via compound-dispatch before subagent dispatch |
| `subagent-driven-development` | Parallel independent tasks | Subagents get "Prior Knowledge" from all 3 memory systems |
| `dispatching-parallel-agents` | 2+ independent tasks | Each agent enriched with file-specific context |
| `requesting-code-review` | After completing features | Review findings saved to MEMORY.md via Post-Review Protocol |
| `receiving-code-review` | Processing review feedback | Feedback routed per Memory Routing Protocol |
| `test-driven-development` | Before implementation | Test patterns informed by claude-mem past test observations |
| `systematic-debugging` | Bug encounters | Queries claude-mem for past fixes on same files |
| `verification-before-completion` | Before claiming done | Checks graphify for untested connected components |
| `finishing-a-development-branch` | Branch completion | Triggers lessons learned capture |

**Superpowers optimization — compound-dispatch integration:**

When superpowers dispatches subagents (SDD, parallel agents, plan execution), the compound-dispatch skill enriches each subagent's prompt with context from all 3 memory systems. This is configured via the global CLAUDE.md protocols (Phase 4).

---

## Phase 3: Install Custom Skills

All skill files are included in the `skills/` directory of this setup package. Copy them to `~/.claude/skills/`:

```bash
# Copy all skills at once
cp -r skills/* ~/.claude/skills/

# Make shell scripts executable
chmod +x ~/.claude/skills/hybrid-search/*.sh
chmod +x ~/.claude/skills/compound-dispatch/gather-context.py
```

### 3.1 Adjust graphify Python path

The `auto-rebuild-graph.sh` script needs to know where pipx installed graphify's Python. Edit it:

```bash
# Find your path:
GRAPHIFY_PYTHON=$(head -1 $(which graphify) | sed 's/#!//')
echo "Your graphify Python: $GRAPHIFY_PYTHON"

# Update the script:
sed -i.bak "s|GRAPHIFY_PYTHON=.*|GRAPHIFY_PYTHON=\"$GRAPHIFY_PYTHON\"|" \
  ~/.claude/skills/hybrid-search/auto-rebuild-graph.sh
```

Or manually edit `~/.claude/skills/hybrid-search/auto-rebuild-graph.sh` line containing `GRAPHIFY_PYTHON=` to match your path.

### 3.2 What each skill does

**graphify/** (1 file) — Orchestrates the graphify CLI for building knowledge graphs from code, docs, papers, and images. Supports modes: deep analysis, incremental update, MCP server, watch mode, wiki generation, Neo4j export.

**hybrid-search/** (10 files) — The core intelligence orchestrator:

| File | Type | Purpose |
|------|------|---------|
| `SKILL.md` | Skill | RRF-fused search across graphify + claude-mem with decay scoring |
| `hook.sh` | PreToolUse hook (Read) | Auto-injects graph neighbors + MEMORY.md entries on file reads. Has session dedup (skip re-enriched files) and token budget (taper at 50KB, stop at 100KB) |
| `auto-rebuild-graph.sh` | PostToolUse hook (Write/Edit/Bash) | Triggers incremental graph rebuild on every code/doc file change. Rate-limited to 30s. Detects git commits on Bash. Runs in background |
| `bump-relevance.sh` | PostToolUse hook (get_observations) | Increments relevance_count for accessed observations, extending their decay half-life |
| `contradiction-check.sh` | PostToolUse hook (*) | Wrapper for contradiction_check.py. Rate-limited to 30s |
| `contradiction_check.py` | Library | Checks new observations against similar older ones using FTS + signal words ("instead", "revert", "wrong"). Score ≥3/7 inserts a contradiction observation |
| `decay.py` | Library | Ebbinghaus decay: `exp(-0.693 * age_days / half_life)`. Base 30-day half-life, extended by access frequency. Crystallized observations get fixed 0.1 decay |
| `crystallize.sh` | SessionEnd hook | Wrapper for crystallize_impl.py |
| `crystallize_impl.py` | Pipeline | Tier 2→3: finds concept clusters with ≥5 observations, distills into structured markdown pages at `~/.claude-mem/crystallized/`. Marks sources with relevance_count=-1 |
| `proceduralize.py` | Pipeline | Tier 3→4: finds repeating (type,concept) subsequences (≥3 steps, ≥3 occurrences), extracts as workflow templates at `~/.claude-mem/procedures/` |

**compound-dispatch/** (2 files) — Unified context bridge for subagents:

| File | Purpose |
|------|---------|
| `SKILL.md` | Instructions for enriching subagent prompts with "Prior Knowledge" from all 3 systems |
| `gather-context.py` | Python script that queries graphify (graph.json), claude-mem (SQLite FTS), and MEMORY.md directly. Cross-system dedup via SequenceMatcher (>60% similarity = duplicate). Auto-detects paths from CWD. Callable by subagents via Bash |

**init-project/** (1 file) — One-command per-project setup. Verifies prerequisites, runs `graphify claude install`, writes enhanced CLAUDE.md with graphify + claude-mem sections, starts claude-mem worker, optionally builds initial graph.

---

## Phase 4: Configure Global Settings

### 4.1 Global settings.json

Write `~/.claude/settings.json` (or merge into existing):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Glob|Grep",
        "hooks": [
          {
            "type": "command",
            "command": "[ -f graphify-out/graph.json ] && echo '{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"additionalContext\":\"graphify: Knowledge graph exists. Read graphify-out/GRAPH_REPORT.md for god nodes and community structure before searching raw files.\"}}' || true"
          }
        ]
      },
      {
        "matcher": "Read",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/skills/hybrid-search/hook.sh"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/skills/hybrid-search/auto-rebuild-graph.sh"
          }
        ]
      },
      {
        "matcher": "Edit",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/skills/hybrid-search/auto-rebuild-graph.sh"
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/skills/hybrid-search/auto-rebuild-graph.sh"
          }
        ]
      },
      {
        "matcher": "mcp__plugin_claude-mem_mcp-search__get_observations",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/skills/hybrid-search/bump-relevance.sh"
          }
        ]
      },
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/skills/hybrid-search/contradiction-check.sh"
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/skills/hybrid-search/crystallize.sh"
          },
          {
            "type": "command",
            "command": "python3 ~/.claude/skills/hybrid-search/proceduralize.py"
          }
        ]
      }
    ]
  },
  "enabledPlugins": {
    "claude-mem@thedotmack": true,
    "superpowers@claude-plugins-official": true
  },
  "extraKnownMarketplaces": {
    "thedotmack": {
      "source": {
        "source": "github",
        "repo": "thedotmack/claude-mem"
      }
    }
  }
}
```

### 4.2 Global CLAUDE.md

Write `~/.claude/CLAUDE.md`:

```markdown
# graphify
- **graphify** (`~/.claude/skills/graphify/SKILL.md`) - any input to knowledge graph. Trigger: `/graphify`
When the user types `/graphify`, invoke the Skill tool with `skill: "graphify"` before doing anything else.

# hybrid-search
- **hybrid-search** (`~/.claude/skills/hybrid-search/SKILL.md`) - fused search across claude-mem (temporal) + graphify (structural) using RRF. Trigger: `/hybrid-search`
When the user types `/hybrid-search`, invoke the Skill tool with `skill: "hybrid-search"` before doing anything else.
Auto-triggers on Read via PreToolUse hook — injects graph neighbor context + MEMORY.md entries for the file being read.

# compound-dispatch
- **compound-dispatch** (`~/.claude/skills/compound-dispatch/SKILL.md`) - enriches subagent prompts with context from all 3 memory systems. Trigger: `/compound-dispatch`
When the user types `/compound-dispatch`, invoke the Skill tool with `skill: "compound-dispatch"` before doing anything else.

## Memory Routing Protocol

When persisting knowledge, route to the correct system:

| What to save | Where | Why |
|-------------|-------|-----|
| User preferences, corrections, feedback | MEMORY.md (`type: feedback`) | Curated, durable, user-controlled |
| Project context, deadlines, stakeholder info | MEMORY.md (`type: project`) | Outlives sessions, needs human curation |
| External resource pointers | MEMORY.md (`type: reference`) | Stable pointers to external systems |
| Bug fixes, decisions, discoveries | claude-mem (auto-captured) | High-volume temporal stream, auto-indexed |
| Code structure, relationships | graphify (auto-discovered) | Derived from source, always fresh via rebuild hooks |
| Conventions for ALL projects | This file (global CLAUDE.md) | Universal rules, not project-specific |

**Before saving to MEMORY.md**, check:
1. Does claude-mem already have an observation covering this? (run `gather-context.py` or `/mem-search`)
2. Is this derivable from the code? (graphify will discover it — don't duplicate)
3. Is this a durable preference or a one-time fact? (one-time → claude-mem; durable → MEMORY.md)

## Post-Review Memory Protocol

After each code quality review completes, save actionable findings as memories:
- Patterns discovered (e.g., "Tiptap v3 uses named exports")
- Conventions established (e.g., "always add immediatelyRender: false for SSR")
- Gotchas encountered (e.g., "Turbopack HMR cache requires server restart")
Save using MEMORY.md with type: feedback and include Why + How to apply.

## Post-Implementation Lessons

After completing all tasks in a plan, save lessons learned:
- Plan steps that needed adjustment (and why)
- Patterns reviewers consistently caught
- What worked well vs. what caused friction
Save as memory with description "Lessons learned: [feature-name]"
```

---

## Phase 5: Superpowers Compound Intelligence Optimizations

The superpowers plugin provides workflow skills out of the box. These optimizations make them work with the compound intelligence stack.

### 5.1 Subagent-Driven Development (SDD) enrichment

When using `/sdd` or the `subagent-driven-development` skill to dispatch implementation subagents:

1. Before dispatching each subagent, run `gather-context.py` for the files that subagent will touch:
   ```bash
   python3 ~/.claude/skills/compound-dispatch/gather-context.py path/to/file1.ts path/to/file2.ts
   ```
2. Include the output as "Prior Knowledge" at the top of the subagent's task prompt
3. Subagents can also self-serve mid-task by running `gather-context.py` via Bash

This is already configured via the compound-dispatch SKILL.md and the global CLAUDE.md. The main agent follows these instructions automatically.

### 5.2 Code review → memory feedback loop

When the `requesting-code-review` skill dispatches a code-reviewer subagent:
- The Post-Review Memory Protocol in global CLAUDE.md instructs Claude to save actionable review findings to MEMORY.md
- Patterns, conventions, and gotchas discovered during review are persisted as `type: feedback` memories
- Future sessions (and subagents via `gather-context.py`) benefit from these findings

### 5.3 Plan execution → lessons learned

When the `executing-plans` skill completes all tasks:
- The Post-Implementation Lessons protocol in global CLAUDE.md triggers lessons capture
- Claude saves what worked, what didn't, and what reviewers caught
- Future planning sessions can query these via `/mem-search lessons-learned`

### 5.4 Brainstorming with structural awareness

When the `brainstorming` skill activates before creative work:
- The PreToolUse Read hook automatically injects graphify community context
- Claude sees what components exist, how they relate, and where new features fit
- Past brainstorming observations from claude-mem inform new ideas

### 5.5 Debugging with temporal context

When the `systematic-debugging` skill activates:
- `gather-context.py --query "error message or symptom"` searches past bug fixes
- Graphify shows connected files that might be affected
- Claude-mem surfaces past fixes on the same files

### 5.6 How it all connects

```
Superpowers Skills (workflow triggers)
    │
    ├── brainstorming ──→ graphify communities + claude-mem past ideas
    ├── writing-plans ──→ claude-mem lessons learned from past plans
    ├── executing-plans ─→ compound-dispatch enriches each subagent
    ├── SDD ────────────→ gather-context.py injects Prior Knowledge
    ├── code-review ────→ findings saved to MEMORY.md (Post-Review Protocol)
    ├── debugging ──────→ claude-mem past fixes + graphify connected files
    └── finishing ──────→ lessons learned captured (Post-Implementation Protocol)
         │
         ▼
    Compound Intelligence Layer
    ├── graphify (structural) ← auto-rebuilt on Write/Edit
    ├── claude-mem (temporal)  ← auto-captured from tool calls
    └── MEMORY.md (curated)   ← saved per routing protocol
```

---

## Phase 6: Per-Project Setup

For each new project, run inside the project directory:

### 6.1 Quick setup with init-project

```
/init-project
```

This verifies prerequisites, writes enhanced CLAUDE.md, and optionally builds the graph.

### 6.2 Or manual setup

```bash
# Build knowledge graph
cd /path/to/project
graphify .    # or use /graphify . inside Claude Code

# Verify graph exists
ls graphify-out/graph.json graphify-out/GRAPH_REPORT.md
```

Add to project CLAUDE.md (create if needed):
```markdown
## graphify — Structural Intelligence
This project has a graphify knowledge graph at `graphify-out/`.
- Before answering architecture questions, read `graphify-out/GRAPH_REPORT.md`
- After modifying code, the graph auto-rebuilds via PostToolUse hooks
- Use `/graphify query "question"` for semantic search

## claude-mem — Temporal Intelligence
This project uses claude-mem for persistent session memory.
- Use `/mem-search <query>` to find past work
- Explain "why" behind decisions — claude-mem captures it

## Compound Intelligence Loop
graphify (structural) + claude-mem (temporal) + MEMORY.md (curated) = unified intelligence.
```

### 6.3 Verify the stack

```bash
# Test graph context injection (replace with a real file from the project)
echo '{"tool_input":{"file_path":"src/main.ts"}}' | bash ~/.claude/skills/hybrid-search/hook.sh

# Test unified context gathering
python3 ~/.claude/skills/compound-dispatch/gather-context.py src/main.ts

# Test auto-rebuild
echo '{"tool_name":"Write","tool_input":{"file_path":"src/main.ts"}}' | bash ~/.claude/skills/hybrid-search/auto-rebuild-graph.sh
sleep 3 && cat /tmp/.graphify-rebuild.log
```

---

## Phase 7: Verification Checklist

- [ ] **Prerequisites**: `graphify --version`, `node --version`, `bun --version`, `python3 --version`
- [ ] **Plugins**: `claude plugins list` shows `claude-mem@thedotmack` and `superpowers@claude-plugins-official`
- [ ] **Skills**: `ls ~/.claude/skills/` shows `graphify/`, `hybrid-search/`, `compound-dispatch/`, `init-project/`
- [ ] **Permissions**: `ls -la ~/.claude/skills/hybrid-search/*.sh` all have execute bit
- [ ] **Settings**: `~/.claude/settings.json` has PreToolUse (Glob|Grep, Read), PostToolUse (Write, Edit, Bash, get_observations, *), SessionEnd hooks
- [ ] **CLAUDE.md**: `~/.claude/CLAUDE.md` has skill triggers, Memory Routing Protocol, Post-Review Protocol, Post-Implementation Lessons
- [ ] **Hook test**: `echo '{"tool_input":{"file_path":"any_file.ts"}}' | bash ~/.claude/skills/hybrid-search/hook.sh` outputs JSON (in a project with graphify-out/)
- [ ] **Context test**: `python3 ~/.claude/skills/compound-dispatch/gather-context.py some_file.ts` outputs "Prior Knowledge" sections
- [ ] **Rebuild test**: auto-rebuild-graph.sh creates `/tmp/.graphify-rebuild.log` with node/edge counts
- [ ] **Rate limit test**: second trigger within 30s produces no rebuild
- [ ] **Live session**: Start Claude Code → Read a file → see "GRAPH CONTEXT for..." injected
- [ ] **Session end**: End a session → `ls ~/.claude-mem/crystallized/` shows knowledge pages
- [ ] **Superpowers**: Start a session → superpowers skills are listed → compound-dispatch enrichment works

---

## Quick Reference

| Command | What it does |
|---------|-------------|
| `/graphify .` | Build/rebuild knowledge graph for current project |
| `/graphify . --update` | Incremental rebuild (only changed files) |
| `/hybrid-search "topic"` | Fused search across temporal + structural |
| `/hybrid-search path "A" "B"` | Find how two concepts connect |
| `/hybrid-search contradictions` | View detected observation conflicts |
| `/hybrid-search crystals` | View Tier 3 crystallized knowledge |
| `/hybrid-search procedures` | View Tier 4 workflow recipes |
| `/hybrid-search promote` | Force-run full 4-tier promotion pipeline |
| `/mem-search "query"` | Search claude-mem observation history |
| `/compound-dispatch` | Enrich subagent prompt with unified context |
| `/init-project` | Set up graphify + claude-mem for current project |
| `python3 ~/.claude/skills/compound-dispatch/gather-context.py <files>` | Direct unified context query (works in subagents) |

---

## Troubleshooting

### Graph rebuild fails with "No module named 'graphify'"
The `GRAPHIFY_PYTHON` variable in `auto-rebuild-graph.sh` must point to the pipx venv Python, not system Python. See Phase 3.1.

### Hook outputs nothing
1. Project must have `graphify-out/graph.json` (run `/graphify .` first)
2. Graph file must be < 500KB (hook skips large graphs for performance)
3. The file basename must match a node in the graph

### Claude-mem not capturing observations
1. Plugin enabled: `claude plugins list | grep claude-mem`
2. Worker running: `curl http://localhost:37777/api/readiness`
3. Restart: `npx claude-mem start`

### Session dedup not working in direct shell tests
Expected. Each `bash` invocation gets a fresh PID. Dedup works within Claude Code sessions where all hook invocations share the parent process PID.

### Superpowers skills not showing
1. Plugin installed: `claude plugins list | grep superpowers`
2. If recently installed, restart Claude Code to load skills
3. Skills appear in the system prompt as available triggers

### gather-context.py returns no results
1. Must be run from within a project directory (walks up to find graphify-out/)
2. Claude-mem DB must exist: `ls ~/.claude-mem/claude-mem.db`
3. At least one session must have been run to populate observations

---

## Changelog

| Date | Change |
|------|--------|
| 2026-04-12 | Initial setup. Full compound intelligence stack: graphify, claude-mem, superpowers, hybrid-search, compound-dispatch, 4-tier knowledge consolidation, session dedup, token budget, MEMORY.md unification, auto-rebuild hooks. Includes all skill files in skills/ directory. |
| 2026-04-12 | Added superpowers integration details: SDD enrichment, code review feedback loop, plan lessons learned, brainstorming structural awareness, debugging temporal context. Added skills/ directory with all 14 files for direct copy. |
