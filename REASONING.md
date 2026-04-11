# Compound Intelligence — Design Reasoning

Why each component exists, how they interact, and the architectural decisions behind the system.

**Last updated:** 2026-04-12

---

## The Core Problem

Claude Code sessions are stateless by default. Each conversation starts from scratch with no knowledge of:
- **What code exists and how it's structured** (structural intelligence)
- **What was done before, what decisions were made, what bugs were fixed** (temporal intelligence)
- **What the user prefers, what conventions matter** (curated intelligence)

Subagents (spawned via the Agent tool) are even worse — they don't even have the parent session's context.

The compound intelligence system solves this by layering three memory systems that each handle a different aspect of knowledge, then unifying them through hooks, skills, and a routing protocol.

---

## The Three Memory Systems

### 1. Graphify — Structural Intelligence

**What it is:** A knowledge graph built from source code and documentation via AST parsing and semantic extraction. Stored as `graphify-out/graph.json`.

**Why it exists:** Reading entire codebases is token-prohibitive (~70x token reduction). The graph provides instant answers to "what exists?", "how do things relate?", and "which files form a logical group?" without reading raw files.

**Key design decisions:**

| Decision | Reasoning |
|----------|-----------|
| AST extraction for code, LLM for docs | Code has deterministic structure (fast, free). Docs need semantic understanding (slow, costs tokens). Split the pipeline accordingly. |
| Community detection | Files naturally cluster into functional groups (UI components, routing, state management). Communities let Claude reason about architectural boundaries without reading every file. |
| God node identification | Some files (like `types.ts` or `architectureDesigner.tsx`) touch everything. Knowing which nodes are hubs prevents naive advice like "just refactor this into smaller files" when the hub serves a structural purpose. |
| Incremental rebuild | Full rebuild takes 30-60s. Incremental (`_rebuild_code`) takes 2-3s with no LLM cost. This makes real-time updates feasible. |
| `.md` files in `DOC_EXTENSIONS` | Documentation IS part of the codebase structure. Not indexing it creates blind spots where Claude can't connect design docs to implementation files. |

### 2. Claude-Mem — Temporal Intelligence

**What it is:** A plugin that auto-captures observations from tool calls into a SQLite database with FTS (full-text search). Stored at `~/.claude-mem/claude-mem.db`.

**Why it exists:** Without temporal memory, Claude resolves the same bugs repeatedly, re-discovers the same architectural patterns, and re-learns user preferences every session. Claude-mem creates a growing corpus of "what happened" that improves over time.

**Key design decisions:**

| Decision | Reasoning |
|----------|-----------|
| Auto-capture (not manual save) | Manual saving creates friction and inconsistency. Auto-capture ensures nothing is lost. The cost is volume, addressed by the 4-tier consolidation pipeline. |
| SQLite with FTS5 | Lightweight, zero-config, works on any system. FTS5 provides good-enough text search without needing a vector DB for most queries. |
| Observation types (bugfix, feature, decision, etc.) | Typed observations enable filtered search. "Show me all decisions about auth" is more useful than "show me everything about auth". |
| 30-day decay half-life | Old observations become less relevant. But frequently accessed ones get extended half-life (bump-relevance.sh). This naturally surfaces what matters and buries what doesn't. |
| SQLite direct access for subagents | Subagents can't use MCP tools (plugin limitation). But they CAN use Bash. `gather-context.py` queries the SQLite DB directly, bypassing the MCP limitation entirely. This was the key insight that made 10/10 effectiveness possible. |

### 3. MEMORY.md — Curated Intelligence

**What it is:** Human-curated memory files in `~/.claude/projects/<slug>/memory/`. Small markdown files with frontmatter (name, description, type).

**Why it exists:** Auto-captured observations are noisy and temporal. Some knowledge is durable and important enough to be explicitly preserved: user preferences, project decisions, external references. MEMORY.md is the "pinned notes" that never decay.

**Key design decisions:**

| Decision | Reasoning |
|----------|-----------|
| Per-project directories | Different projects have different conventions. A React preference shouldn't pollute a Go project's context. |
| Frontmatter-based format | Machine-readable metadata (type, name, description) enables programmatic scanning while keeping files human-editable. |
| Always loaded in context | MEMORY.md is injected at session start. Unlike claude-mem (queried on demand), curated memories are always available. This ensures preferences are never forgotten. |
| Separate from CLAUDE.md | CLAUDE.md is for instructions ("do X"). MEMORY.md is for knowledge ("X is true"). Mixing them dilutes both. |

---

## The Unification Layer

### Why unification matters

Three separate systems create three problems:
1. **Same knowledge, different places** — "use focus effect not dim effect" might be in MEMORY.md AND a claude-mem observation
2. **Incomplete injection** — graphify neighbors are injected on Read, but MEMORY.md entries weren't
3. **Subagent amnesia** — subagents get none of it

### How unification works

**Read path (hook.sh):**
When Claude reads a file, the PreToolUse hook on Read injects:
- Graphify neighbors (structural: "Header.tsx imports from types.ts")
- MEMORY.md entries (curated: "use focus effect terminology")
- Session dedup prevents re-injection
- Token budget tapers injection after 50KB, stops at 100KB

**Query path (gather-context.py):**
Direct query to all three systems with cross-system dedup:
- Graphify → graph.json node lookup + neighbor traversal
- Claude-mem → SQLite FTS query
- MEMORY.md → keyword scan of memory files
- SequenceMatcher dedup removes >60% similar entries across systems

**Write path (Memory Routing Protocol in CLAUDE.md):**
Clear routing rules prevent duplicate storage:
- Preferences → MEMORY.md
- Temporal facts → claude-mem (auto)
- Code structure → graphify (auto)
- Universal rules → global CLAUDE.md

---

## The 4-Tier Knowledge Consolidation Pipeline

Raw observations grow unboundedly. Without consolidation, search quality degrades and token costs increase.

### Tier 1: Raw Observations (claude-mem auto-capture)
- **Volume:** High (10-50 per session)
- **Decay:** Ebbinghaus curve, 30-day half-life
- **Purpose:** Capture everything; let consolidation sort it out

### Tier 2: Indexed Observations (FTS + decay scoring)
- **Trigger:** Automatic (every observation is indexed)
- **Purpose:** Fast search with relevance ranking
- **Scoring:** `decay * type_weight * access_frequency`

### Tier 3: Crystallized Knowledge (crystallize_impl.py)
- **Trigger:** SessionEnd hook, when concept clusters have ≥5 observations
- **Purpose:** Merge related observations into structured knowledge pages
- **Output:** `~/.claude-mem/crystallized/{hash}.md` with Key Facts, Decisions, Bugs, Timeline
- **Effect:** Source observations get `relevance_count = -1` (decay floor)
- **Regrowth:** ≥3 new observations trigger re-crystallization

### Tier 4: Procedural Knowledge (proceduralize.py)
- **Trigger:** SessionEnd hook, after crystallization
- **Purpose:** Extract repeating action patterns into workflow recipes
- **Detection:** Looks for (type, concept) subsequences of length ≥3 appearing ≥3 times
- **Output:** `~/.claude-mem/procedures/{hash}.md` with Steps, Files, Concepts

**Why this tiering:** Raw observations are great for search but terrible for reasoning. Crystals are great for understanding but too coarse for search. Procedures are great for repeating tasks but useless for novel work. Each tier serves a different need.

---

## The Hook Architecture

### PreToolUse Hooks (fire BEFORE a tool executes)

| Hook | Trigger | Purpose | Design Reasoning |
|------|---------|---------|-----------------|
| Glob/Grep advisory | Glob or Grep | Reminds Claude that a graph exists | Prevents Claude from doing expensive file searches when `GRAPH_REPORT.md` has the answer. Cheap (~20 tokens injected). |
| hook.sh | Read | Injects graph context + MEMORY.md | The most impactful hook. Every file read gets structural context for free. Session dedup prevents token bloat. |

### PostToolUse Hooks (fire AFTER a tool executes)

| Hook | Trigger | Purpose | Design Reasoning |
|------|---------|---------|-----------------|
| auto-rebuild-graph.sh | Write, Edit, Bash | Real-time graph freshness | Previous design only rebuilt after git commits. Files could be created, modified, deleted — all invisible to the graph until commit. Now every Write/Edit triggers incremental rebuild. Rate-limited to 30s to avoid thrashing. |
| bump-relevance.sh | get_observations | Extends decay for accessed obs | Observations that Claude actively retrieves are clearly useful. Bumping their relevance_count extends their half-life, keeping them alive longer. |
| contradiction-check.sh | * (all tools) | Detects conflicting observations | Decisions get reversed, approaches change. Without conflict detection, claude-mem silently holds contradictory information. Rate-limited to 30s. |

### SessionEnd Hooks (fire when conversation ends)

| Hook | Trigger | Purpose | Design Reasoning |
|------|---------|---------|-----------------|
| crystallize.sh | SessionEnd | Tier 2→3 promotion | Sessions generate lots of raw observations. Crystallization merges them into lasting knowledge. Running at session end ensures all observations from the session are captured. |
| proceduralize.py | SessionEnd | Tier 3→4 promotion | Procedural patterns only emerge across sessions. Running after crystallization ensures the latest crystals are included. |

---

## Session Dedup + Token Budget

### Problem
Without dedup, reading the same file multiple times (common during debugging) injects the same graph context each time. Over a long session, cumulative injection wastes context window.

### Solution: Two-tier protection

**Session dedup (per-file):**
- Track enriched files in `/tmp/.hybrid-search-session-$PPID`
- Skip re-injection for already-enriched files
- PID-scoped to the Claude Code process (all hook calls share PPID)
- Auto-cleanup: files >2 hours old are deleted

**Token budget (per-session):**
- Track cumulative injected bytes in the session file
- 0-50KB: Full injection (graph + MEMORY.md)
- 50-100KB: Graph-only (drop MEMORY.md to save tokens)
- >100KB: Stop automatic injection entirely
- User can always use `/hybrid-search` manually to bypass

### Why these thresholds
- 50KB ≈ 12,500 tokens (reasonable for context enrichment)
- 100KB ≈ 25,000 tokens (starts competing with actual work for context window)
- These are conservative — adjust based on the model's context window size

---

## Cross-System Deduplication

### Problem
"Use focus effect, not dim effect" exists in both MEMORY.md (as curated feedback) and claude-mem (as an auto-captured observation). Injecting both wastes tokens and looks sloppy.

### Solution
`gather-context.py` uses `difflib.SequenceMatcher` to detect >60% similarity between MEMORY.md entries and claude-mem observations. When overlap is detected, the claude-mem observation is dropped (MEMORY.md is curated and therefore higher quality).

### Why 60% threshold
- Too low (40%): Drops legitimately different entries that share some vocabulary
- Too high (80%): Only catches near-exact duplicates
- 60% was empirically tested — catches "focus effect" overlap while preserving distinct observations about the same file

---

## Subagent Context Bridge

### Problem
Subagents dispatched via the Agent tool start with zero context. They can't:
- Call MCP tools (plugin limitation — no claude-mem access)
- Read the parent session's conversation history
- Know about file relationships or past decisions

### Solution: gather-context.py

A Python script that queries all three systems directly:
- **Graphify:** Reads `graph.json` (file I/O, no MCP needed)
- **Claude-mem:** Queries SQLite DB with FTS (direct DB access, no MCP needed)
- **MEMORY.md:** Scans project memory directory (file I/O, no MCP needed)

The main agent runs this before dispatching a subagent and includes the output as "Prior Knowledge" in the prompt. Subagents can also call it mid-task via Bash.

### Why this bypasses the MCP limitation
MCP tools require the plugin runtime. But the data is just files and a SQLite database. Python can read both. The key insight: **you don't need the API if you can access the storage directly.**

---

## Auto-Rebuild: Why Write/Edit, Not Just Commits

### Previous design
Graph only rebuilt after `git commit` (detected via PostToolUse on Bash).

### Problem
During active implementation, files are created and modified many times before committing. The graph is stale for the entire implementation session — exactly when structural intelligence is most needed.

### New design
PostToolUse hooks on Write AND Edit trigger `_rebuild_code()`:
- Code files get AST extraction (fast, no LLM)
- Doc files get detected but may need semantic extraction (flagged for manual rebuild)
- Rate-limited to 30s to prevent thrashing during rapid edits
- Runs in background (non-blocking)

### Why rate limiting matters
A typical implementation session might trigger 50+ Write/Edit operations. Without rate limiting, each would spawn a rebuild (2-3s each, but they'd queue up). 30s rate limiting means at most 2 rebuilds per minute, which keeps the graph fresh without impacting performance.

---

## Memory Routing Protocol

### Problem
Three memory systems = three possible places to save anything. Without clear routing, the same information ends up in multiple places (waste) or the wrong place (ineffective).

### Solution: Routing table in global CLAUDE.md

| Knowledge type | System | Why this system |
|---------------|--------|-----------------|
| Preferences | MEMORY.md | Durable, curated, always loaded |
| Temporal facts | claude-mem | Auto-captured, searchable, decays naturally |
| Code structure | graphify | Derived from source, always accurate |
| Universal rules | global CLAUDE.md | Applies everywhere, always loaded |

### The "before saving" checklist
1. **Already in claude-mem?** → Don't duplicate
2. **Derivable from code?** → graphify will find it
3. **Durable or one-time?** → Durable = MEMORY.md, one-time = claude-mem

This prevents the most common failure mode: saving everything to MEMORY.md until it becomes a dumping ground.

---

## Superpowers Integration

### What superpowers is

Superpowers is a Claude Code plugin that provides structured workflow skills: brainstorming, planning, TDD, code review, debugging, SDD (Subagent-Driven Development), etc. These are "rigid" skills — they enforce discipline (e.g., "always brainstorm before building", "always run tests before claiming done").

### Why it matters for compound intelligence

Without superpowers, compound intelligence is passive — it answers questions and injects context. With superpowers, it becomes active — it shapes the workflow at every stage:

| Workflow Stage | Without Superpowers | With Superpowers + Compound Intelligence |
|---------------|--------------------|-----------------------------------------|
| Planning | Ad-hoc, no learning | Queries claude-mem for past lessons before planning |
| Implementation | Subagents start blank | Each subagent gets Prior Knowledge from all 3 systems |
| Review | Findings are ephemeral | Post-Review Protocol saves findings to MEMORY.md |
| Completion | No retrospective | Post-Implementation Lessons captured for future plans |
| Debugging | Start from scratch | Past fixes on same files surfaced automatically |

### Key integration points

**SDD enrichment (the biggest win):**
SDD dispatches multiple subagents in parallel, each working on an independent task. Without compound-dispatch, each subagent starts with zero context about the codebase. With it, each gets:
- Which community the files belong to (graphify)
- Past decisions and bugs related to those files (claude-mem FTS)
- User preferences applicable to the work (MEMORY.md)

This turns subagents from "smart but ignorant workers" into "smart workers briefed on project history."

**Code review → memory feedback loop:**
The `requesting-code-review` skill dispatches a code-reviewer subagent. The Post-Review Memory Protocol (in global CLAUDE.md) ensures actionable findings get saved as `type: feedback` memories. This creates a positive feedback loop:
1. Reviewer catches a pattern (e.g., "missing SSR guard")
2. Finding saved to MEMORY.md
3. Future sessions see the finding via hook.sh injection
4. The pattern is caught proactively, not just reactively

**Planning with historical awareness:**
The `writing-plans` skill benefits from claude-mem's temporal memory. Before writing a plan, querying `/mem-search lessons-learned` surfaces:
- Which plan steps needed adjustment in past projects
- Patterns reviewers consistently caught (so the plan can address them upfront)
- Time estimates that proved accurate or inaccurate

**Debugging with full context:**
The `systematic-debugging` skill can leverage all 3 systems:
- graphify: "what other files are connected to the buggy file?" (find blast radius)
- claude-mem: "have we fixed a similar bug before?" (find past solutions)
- MEMORY.md: "are there known gotchas with this area?" (avoid re-learning)

### Why protocols, not hooks

The superpowers integration uses CLAUDE.md protocols (instructions Claude follows) rather than automated hooks because:

1. **Review findings are subjective** — a hook can't decide which findings are worth saving. Claude needs to make that judgment.
2. **Lessons learned need synthesis** — it's not about saving raw data but distilling what was learned. This requires reasoning.
3. **Memory routing needs context** — deciding whether something goes in MEMORY.md vs letting claude-mem capture it requires understanding the nature of the knowledge.

Hooks work for mechanical tasks (rebuild graph, bump relevance). Protocols work for judgment tasks (save findings, capture lessons).

---

## Changelog

| Date | Change |
|------|--------|
| 2026-04-12 | Initial document created. Covers all 3 memory systems, unification layer, 4-tier pipeline, hook architecture, session dedup, token budget, cross-system dedup, subagent bridge, auto-rebuild, memory routing. |
| 2026-04-12 | Added superpowers integration reasoning: SDD enrichment, code review feedback loop, planning with historical awareness, debugging with full context, protocols vs hooks design choice. |
