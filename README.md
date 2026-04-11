# Compound Intelligence for Claude Code

## Why

Every conversation with an AI coding assistant starts from zero. It doesn't know what you built yesterday, why you made the decisions you made, how your files relate to each other, or what you've told it a hundred times before. You end up re-explaining context, re-solving bugs you already fixed, and watching subagents make mistakes you could have prevented with a single sentence of background.

The cost isn't just tokens or time. It's the compounding loss of everything the AI could have learned from working with you — patterns it spotted, architectural choices it helped you reason through, gotchas it discovered the hard way. All of it evaporates when the session ends.

We believe an AI assistant should get smarter the more you work with it. Not through fine-tuning or model updates, but through memory — structural, temporal, and curated — that persists across sessions and flows to every subagent it spawns.

That's what this system does. It gives Claude Code a memory that compounds.

---

## How

Three memory systems, each handling a different dimension of knowledge, unified through a single intelligence layer.

**Structural memory (graphify)** answers: *What exists and how does it connect?*

Your codebase is parsed into a knowledge graph — files, functions, imports, communities of related modules. Instead of reading thousands of files to understand architecture, Claude reads a graph of relationships. Every time you edit a file, the graph rebuilds automatically. The structure is always current.

**Temporal memory (claude-mem)** answers: *What happened and why?*

Every session automatically captures decisions, bug fixes, discoveries, and feature implementations as searchable observations. They decay over time (old facts matter less), but frequently accessed ones stay alive longer. When enough observations cluster around a concept, they crystallize into structured knowledge pages. When the same workflow repeats across sessions, it's extracted as a reusable procedure. Knowledge consolidates itself.

**Curated memory (MEMORY.md)** answers: *What does the user care about?*

Some things shouldn't be auto-captured or auto-decayed. Your preferences ("call it focus effect, not dim effect"), your feedback ("extract hooks when this file grows"), your project context ("merge freeze starts Thursday"). These are explicitly saved, always loaded, and never forgotten.

**The unification layer** makes them work as one:

- When Claude reads a file, it sees graph neighbors AND relevant memories AND past observations — injected automatically, deduplicated, with a token budget so it doesn't overwhelm the context.
- When Claude dispatches a subagent, it queries all three systems and briefs the subagent with "Prior Knowledge" before it starts work.
- When Claude needs to save something, a routing protocol directs it to the right system — no duplicates across systems.
- When a session ends, raw observations promote through four tiers: working memory → episodic → crystallized knowledge → procedural workflows.

**Workflow intelligence (superpowers)** makes it proactive:

Structured skills enforce discipline at every stage — brainstorm before building, plan before coding, review before merging, debug systematically. Each skill is wired into the compound intelligence layer: plans draw on past lessons, reviews save findings for the future, subagents start briefed instead of blank.

---

## What

A portable setup package that gives any Claude Code installation the full compound intelligence stack.

**What you get:**

- Real-time structural awareness of your codebase (auto-rebuilding knowledge graph)
- Persistent cross-session memory that compounds over time (auto-captured observations with decay + crystallization)
- Curated preferences that are always in context (never re-explain the same thing)
- Subagents that start informed, not blank (unified context injection from all 3 systems)
- Structured workflows that learn from past work (review findings saved, lessons captured, plans informed by history)
- Token-efficient context injection (session dedup, budget tiers, cross-system dedup)
- Automatic knowledge consolidation (4-tier pipeline: raw → episodic → crystallized → procedural)
- Contradiction detection (catches when new observations conflict with old ones)

**What's in this package:**

| File | Purpose |
|------|---------|
| `SETUP.md` | Step-by-step installation guide (7 phases, from prerequisites to verification) |
| `REASONING.md` | Design explanations for every component (the engineering "why" behind each decision) |
| `README.md` | This file (the human "why" — purpose, approach, outcome) |
| `skills/` | All 14 skill files, ready to copy to `~/.claude/skills/` |

**What it takes to set up:**

1. Install graphify, claude-mem plugin, superpowers plugin
2. Copy the `skills/` directory
3. Write `settings.json` (hooks) and `CLAUDE.md` (protocols)
4. Run `/init-project` in each project

Full instructions in [SETUP.md](SETUP.md). Full reasoning in [REASONING.md](REASONING.md).

---

*The best tool isn't the one that's smartest in a single conversation. It's the one that remembers what it learned and applies it next time.*
