# hybrid-search

Fused search across **claude-mem** (temporal memory) and **graphify** (structural code graph)
using Reciprocal Rank Fusion (RRF). Concepts that appear in both streams rank highest. Also
ships the helper scripts that wire compound intelligence together: auto-rebuild-graph,
crystallize, contradiction-check, proceduralize, decay, bump-relevance.

## Trigger

```
/hybrid-search "query"
```

## Variants

| Command | What it does |
|---|---|
| `/hybrid-search "query"` | Fused search, RRF-ranked across both memory systems |
| `/hybrid-search "query" --graph-only` | Skip claude-mem, traverse the graph only |
| `/hybrid-search contradictions` | View detected observation conflicts |
| `/hybrid-search crystals` | View crystallized knowledge pages from past sessions |
| `/hybrid-search procedures` | View extracted workflow recipes |

## Hook scripts shipped

These scripts are referenced by global hook entries in `~/.claude/settings.json` (written by
the `workdir` bootstrap step):

| Script | Hook event | What it does |
|---|---|---|
| `hook.sh` | PreToolUse on Read | Inject graph neighbour + MEMORY.md context for files being read (session-deduped, token-budgeted) |
| `auto-rebuild-graph.sh` | PostToolUse on Write/Edit/Bash | Incremental graphify rebuild on code changes (rate-limited to 30s) |
| `bump-relevance.sh` | PostToolUse on observation access | Increment relevance counter so frequently-accessed observations decay slower |
| `contradiction-check.sh` | PostToolUse on `*` | Flag new observations that conflict with similar older ones |
| `crystallize.sh` | SessionEnd | Promote concept clusters into structured pages at `~/.claude-mem/crystallized/` |
| `proceduralize.py` | SessionEnd | Extract repeated workflows as reusable templates at `~/.claude-mem/procedures/` |
| `decay.py` | (cron / manual) | Apply Ebbinghaus decay to claude-mem observations |

## Installation

This skill is bundled with `workdir`. The bootstrap subcommand copies it to
`~/.claude/skills/hybrid-search/` so the global hook paths in `~/.claude/settings.json`
resolve correctly:

```
/workdir bootstrap
```

Or install standalone:

```
/plugin install hybrid-search@claude-init
```

## Layout

```
plugins/hybrid-search/
├── .claude-plugin/plugin.json
├── hooks/
│   ├── hooks.json
│   └── check-update.sh
└── skills/hybrid-search/
    ├── SKILL.md
    ├── hook.sh                       # Read PreToolUse — context injection
    ├── auto-rebuild-graph.sh         # Write/Edit/Bash PostToolUse — graphify update
    ├── bump-relevance.sh             # observation-access counter
    ├── contradiction-check.sh        # contradiction detection wrapper
    ├── contradiction_check.py        # contradiction detection logic
    ├── crystallize.sh                # SessionEnd — crystallize observations
    ├── crystallize_impl.py           # crystallize logic
    ├── proceduralize.py              # SessionEnd — extract workflow procedures
    └── decay.py                      # Ebbinghaus decay over claude-mem observations
```
