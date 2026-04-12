# Compound Intelligence for Claude Code

A portable setup package that gives Claude Code persistent memory across sessions — structural awareness of your codebase, temporal memory of past decisions, and curated preferences that never need repeating. Claude gets smarter the more you work with it.

---

## Setup

Paste this into Claude Code and it will handle everything:

```
Set up compound intelligence using https://github.com/bkirosangma/claude-init — follow the SETUP.md instructions
```

Claude will read the repo, install the prerequisites, copy the skills, configure the hooks, and initialize your project.

For manual setup or troubleshooting, see [SETUP.md](SETUP.md).

---

## Usage

Once set up, most of the system works automatically. Here's what you should know as a user.

### What Happens Automatically

- **On file read** — Claude sees graph neighbors and relevant memories injected into context (deduplicated, token-budgeted)
- **On file write/edit** — The knowledge graph rebuilds incrementally (rate-limited to 30s)
- **On session end** — Observations promote through four tiers: raw → episodic → crystallized → procedural
- **On subagent dispatch** — Each subagent is briefed with "Prior Knowledge" from all three memory systems

### Commands You Can Use

| Command | What it does |
|---------|-------------|
| `/graphify .` | Build or rebuild the knowledge graph for the current project |
| `/graphify . --update` | Incremental rebuild (only changed files) |
| `/graphify query "question"` | Semantic search across the codebase |
| `/hybrid-search "topic"` | Fused search across temporal + structural memory |
| `/hybrid-search contradictions` | View detected observation conflicts |
| `/hybrid-search crystals` | View crystallized knowledge pages |
| `/hybrid-search procedures` | View extracted workflow recipes |
| `/mem-search "query"` | Search claude-mem observation history |
| `/compound-dispatch` | Enrich a subagent prompt with unified context |
| `/init-project` | Set up compound intelligence in a new project |

### Day-to-Day Workflow

1. **Start coding.** Memory captures automatically — decisions, bug fixes, discoveries all become searchable observations.
2. **Explain the "why" when it matters.** Claude-mem captures your reasoning, making it available in future sessions.
3. **Use `/hybrid-search` when you need context.** It searches across both the knowledge graph and past observations, ranked by relevance.
4. **Use `/graphify query` for architecture questions.** The graph provides ~70x token reduction vs reading raw files.
5. **Let preferences stick.** Corrections and feedback are saved to MEMORY.md and applied in every future session.

---

## Skills

This package includes 4 custom skills and 10 supporting scripts.

| Skill | Trigger | What it does |
|-------|---------|--------------|
| **graphify** | `/graphify` | Turns any folder of files (code, docs, papers, images) into a navigable knowledge graph with community detection, an interactive HTML visualization, GraphRAG-ready JSON, and a plain-language `GRAPH_REPORT.md`. Supports incremental rebuilds, directed graphs, Neo4j export, Obsidian vaults, and an agent-crawlable wiki. |
| **hybrid-search** | `/hybrid-search` | Fused search combining claude-mem's temporal memory (vector + keyword) with graphify's structural knowledge graph (BFS/DFS traversal), ranked by Reciprocal Rank Fusion. Also manages the 4-tier knowledge consolidation pipeline — contradiction detection, confidence decay scoring, crystallized knowledge pages, and procedural workflow extraction. Includes 8 supporting hooks and scripts that run automatically on file reads, writes, and session end. |
| **compound-dispatch** | `/compound-dispatch` | Enriches subagent prompts with "Prior Knowledge" from all three memory systems before dispatching them. Queries graphify for structural relationships, claude-mem for past decisions and observations, and MEMORY.md for user preferences — so subagents start informed instead of blank. |
| **init-project** | `/init-project` | One-command per-project setup. Verifies global prerequisites, installs graphify's Claude Code integration, writes an enhanced CLAUDE.md with all memory routing protocols, creates ignore files, starts the claude-mem worker, and optionally builds the initial knowledge graph. |

The superpowers plugin adds additional workflow skills (brainstorming, TDD, debugging, planning, code review, and more) that integrate with the compound intelligence layer. See [SETUP.md](SETUP.md) for the full list.

---

## Why, How, and What

### Why

Every conversation with an AI coding assistant starts from zero. It doesn't know what you built yesterday, why you made the decisions you made, how your files relate to each other, or what you've told it a hundred times before. You end up re-explaining context, re-solving bugs you already fixed, and watching subagents make mistakes you could have prevented with a single sentence of background.

The cost isn't just tokens or time. It's the compounding loss of everything the AI could have learned from working with you — patterns it spotted, architectural choices it helped you reason through, gotchas it discovered the hard way. All of it evaporates when the session ends.

An AI assistant should get smarter the more you work with it. Not through fine-tuning or model updates, but through memory — structural, temporal, and curated — that persists across sessions and flows to every subagent it spawns.

### How

Three memory systems, each handling a different dimension of knowledge, unified through a single intelligence layer.

**Structural memory (graphify)** answers: *What exists and how does it connect?*
Your codebase is parsed into a knowledge graph — files, functions, imports, communities of related modules. Instead of reading thousands of files to understand architecture, Claude reads a graph of relationships. Every time you edit a file, the graph rebuilds automatically.

**Temporal memory (claude-mem)** answers: *What happened and why?*
Every session automatically captures decisions, bug fixes, discoveries, and feature implementations as searchable observations. They decay over time (Ebbinghaus curve, 30-day half-life), but frequently accessed ones stay alive longer. When enough observations cluster around a concept, they crystallize into structured knowledge pages. When the same workflow repeats, it's extracted as a reusable procedure.

**Curated memory (MEMORY.md)** answers: *What does the user care about?*
Your preferences, feedback, project context, and external references. Explicitly saved, always loaded, never auto-decayed.

**The unification layer** makes them work as one:
- File reads inject graph neighbors + relevant memories + past observations (deduplicated, token-budgeted)
- Subagent dispatches brief each agent with "Prior Knowledge" from all three systems
- A routing protocol directs saves to the right system — no cross-system duplicates
- Session end promotes raw observations through four tiers: working memory → episodic → crystallized → procedural

**Workflow intelligence (superpowers)** makes it proactive:
Structured skills enforce discipline at every stage — brainstorm before building, plan before coding, review before merging, debug systematically. Each skill is wired into the compound intelligence layer.

### What

| What you get | How |
|-------------|-----|
| Real-time structural awareness | Auto-rebuilding knowledge graph |
| Persistent cross-session memory | Auto-captured observations with decay + crystallization |
| Curated preferences always in context | MEMORY.md, never re-explain the same thing |
| Subagents that start informed | Unified context injection from all 3 systems |
| Structured workflows that learn | Review findings saved, lessons captured, plans informed by history |
| Token-efficient context injection | Session dedup, budget tiers, cross-system dedup |
| Automatic knowledge consolidation | 4-tier pipeline: raw → episodic → crystallized → procedural |
| Contradiction detection | Catches when new observations conflict with old ones |

---

## Credits and References

This system is built on top of these tools:

| Tool | Author | Link | Role in the stack |
|------|--------|------|-------------------|
| **Claude Code** | Anthropic | [claude.ai/download](https://claude.ai/download) | The AI coding assistant this system extends |
| **graphify** | graphifyy | [PyPI](https://pypi.org/project/graphifyy/) | Structural intelligence — knowledge graph generation and community detection |
| **claude-mem** | thedotmack | [GitHub Marketplace](https://github.com/thedotmack/claude-mem) | Temporal intelligence — persistent cross-session observation memory with FTS5 search |
| **superpowers** | claude-plugins-official | [Claude Plugins](https://github.com/claude-plugins-official/superpowers) | Workflow intelligence — structured skills for brainstorming, TDD, debugging, planning, and code review |

---

**Detailed setup instructions:** [SETUP.md](SETUP.md)
**Design decisions and reasoning:** [REASONING.md](REASONING.md)

---

*The best tool isn't the one that's smartest in a single conversation. It's the one that remembers what it learned and applies it next time.*
