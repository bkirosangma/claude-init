# compound-dispatch

Enriches subagent prompts with **"Prior Knowledge"** drawn from all three memory systems —
graphify (structural), claude-mem (temporal), and MEMORY.md (curated) — before they're
dispatched. Bridges the gap where subagents normally start with blank context.

## Trigger

```
/compound-dispatch
```

Or invoked indirectly by other skills (notably `superpowers` skills that dispatch subagents)
which delegate prompt enrichment to this skill before calling the Agent tool.

## What it injects

For a given subagent task, `gather-context.py` produces a "Prior Knowledge" block containing:

- **Structural**: graph neighbours of files mentioned in the task (from `graphify-out/graph.json`)
- **Temporal**: relevant past observations from claude-mem (semantic + keyword search)
- **Curated**: matching feedback/preference/project memories from MEMORY.md
- **Crystallized**: concept clusters from `~/.claude-mem/crystallized/` if any apply
- **Procedural**: extracted workflow recipes from `~/.claude-mem/procedures/` if applicable

The block is **session-deduped** (so the same context isn't injected twice in one session) and
**token-budgeted** (so it stays under a configured cap).

## When to use

- Before dispatching any subagent via the Agent tool for implementation work
- Especially important for `superpowers:executing-plans` and
  `superpowers:subagent-driven-development` flows where each subtask runs in isolation
- When a subagent needs to understand file relationships, past decisions, or user preferences
  that aren't visible in the task prompt alone

## Installation

Bundled with `workdir`. Copied to `~/.claude/skills/compound-dispatch/` by the bootstrap
subcommand:

```
/workdir bootstrap
```

Or standalone:

```
/plugin install compound-dispatch@claude-init
```

## Layout

```
plugins/compound-dispatch/
├── .claude-plugin/plugin.json
├── hooks/
│   ├── hooks.json
│   └── check-update.sh
└── skills/compound-dispatch/
    ├── SKILL.md
    └── gather-context.py     # builds the Prior Knowledge block from all 3 memory systems
```
