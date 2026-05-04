---
name: hybrid-search
description: Fused search with RRF, confidence decay, contradiction detection, 4-tier knowledge consolidation
trigger: /hybrid-search
---

# /hybrid-search

Fused search that combines claude-mem's temporal memory (vector + keyword) with graphify's structural knowledge graph (BFS/DFS traversal). Returns results ranked by Reciprocal Rank Fusion (RRF) — concepts that appear in multiple streams rank highest.

## Usage

```
/hybrid-search "query"                    # fused search across both systems (with decay scoring)
/hybrid-search "query" --graph-only       # only graph traversal (skip claude-mem)
/hybrid-search "query" --mem-only         # only claude-mem (skip graph)
/hybrid-search path "NodeA" "NodeB"       # shortest path + temporal history for each hop
/hybrid-search contradictions             # review detected observation conflicts
/hybrid-search crystals                   # list Tier 3 crystallized knowledge pages
/hybrid-search crystals "topic"           # read a specific crystal
/hybrid-search procedures                 # list Tier 4 workflow recipes
/hybrid-search procedures "topic"         # read a specific procedure
/hybrid-search promote                    # force-run the full 4-tier promotion pipeline now
```

## How It Works

### Step 1: Parallel Search

Run both search streams simultaneously:

**Stream A — claude-mem (temporal):**
Use the `mcp__plugin_claude-mem_mcp-search__search` tool:
```
search(query="<user query>", limit=15)
```
This returns observation IDs ranked by vector similarity + keyword match.

**Stream B — graphify (structural):**
First, check if `graphify-out/graph.json` exists in the current project. If not, skip this stream and return claude-mem results only.

**Adaptive strategy based on graph size:**
- Read file size of `graphify-out/graph.json` using Bash: `stat -f%z graphify-out/graph.json` (macOS) or `stat -c%s` (Linux)
- If **<=500KB** (~500 nodes): Use **direct read** — read graph.json with the Read tool, then perform in-context BFS:
  1. Extract query terms (words > 2 chars, lowercased)
  2. Score each node: count of query terms appearing in `node.label` (case-insensitive)
  3. Pick top 3 nodes as start points
  4. BFS 2 layers deep: collect all neighbors within 2 hops
  5. Collect edges between visited nodes with their `relation` and `confidence` fields
  6. Rank results by: (a) proximity to start nodes, (b) edge confidence scores

- If **>500KB**: Use **graphify MCP** — check if graphify MCP tools are available:
  - If available: call `query_graph(question="<query>", mode="bfs", depth=2)`
  - If not: tell the user to start it with `/graphify . --mcp`, then fall back to claude-mem only

### Step 2: Cross-Reference

For the top 5 graph nodes found in Stream B, search claude-mem by file path:
```
search(query="<node.source_file>", limit=3)
```
This finds temporal observations (past changes, decisions, bugfixes) related to each structural result.

### Step 3: Reciprocal Rank Fusion

Merge results from all streams using RRF:

```
k = 60  (standard constant)

For each unique result (identified by file path or concept name):
  rrf_score = 0
  If in claude-mem results at rank R:  rrf_score += 1/(60 + R)
  If in graph results at rank R:       rrf_score += 1/(60 + R)
  If in cross-reference results:       rrf_score += 0.005  (small bonus)

Sort by rrf_score descending. Take top 10.
```

### Step 4: Enriched Output

For each top result, present BOTH structural and temporal context:

```
## [1] scheduleRecord (architectureDesigner.tsx:133)  RRF: 0.0323

GRAPH: Called by useDragEndRecorder, useLabelEditing, useCanvasInteraction
       Community: History Management (community 3)
       Path to useActionHistory: scheduleRecord -> history.recordAction (1 hop)

HISTORY: [2h ago] Fixed to use 'Edit conditional' label for condition nodes
         [3d ago] Extracted as part of hook refactoring
         Type: bugfix, refactor
```

Then fetch full observation details for any the user wants to dive into:
```
get_observations(ids=[153, 142])
```

### Step 5: Save Result (optional)

If the hybrid search produced a useful finding, save it as a graphify result:
```
graphify save-result --question "<query>" --answer "<summary>" --type hybrid_query --nodes <node1> <node2>
```

## Path Mode

For `/hybrid-search path "A" "B"`:

1. Find shortest path in graphify graph (direct read or MCP `shortest_path`)
2. For EACH node along the path, search claude-mem for related observations
3. Present the path with temporal annotations:
   ```
   useDragEndRecorder --calls--> scheduleRecord --calls--> history.recordAction
       |                            |                            |
       [Fixed today: ref            [Fixed today: Edit           [No recent
        for conditional label]       conditional label]           changes]
   ```

## When There's No Graph

If `graphify-out/graph.json` doesn't exist in the current project:
- Log: "No graphify graph found. Running claude-mem search only."
- Return claude-mem results without graph enrichment
- Suggest: "Run `/graphify` to build a knowledge graph for this project."

## Auto-Trigger Integration

This skill also powers an auto-trigger hook on `Read` operations. When a file is read:
1. The hook finds the file's node in the graph
2. Returns a compact context block with structural neighbors
3. This is injected alongside claude-mem's existing temporal context

See `~/.claude/skills/hybrid-search/hook.sh` for the auto-trigger implementation.

---

## Confidence Decay (Forgetting Curve)

All search results are scored with an Ebbinghaus-inspired decay function:

```
decay = exp(-0.693 * age_days / half_life)
```

- **Base half-life:** 30 days (observations lose half their weight per month)
- **Reinforced observations:** Each time an observation is fetched via `get_observations`, its `relevance_count` increments, extending its half-life: `half_life = 30 * (1 + 0.5 * relevance_count)`
- **Crystallized observations:** `relevance_count = -1` → fixed decay of 0.1 (value captured in the crystal)

The decay multiplier is applied after RRF fusion: `final_score = rrf_score * decay`

Implementation: `~/.claude/skills/hybrid-search/decay.py`
Relevance tracking: `~/.claude/skills/hybrid-search/bump-relevance.sh` (PostToolUse hook on `get_observations`)

After Step 3 (RRF), apply decay:

1. For each fused result, fetch `created_at_epoch` and `relevance_count` from the DB
2. Compute decay score using `decay.py:compute_decay()`
3. Multiply: `final_score = rrf_score * decay`
4. Re-rank by final_score

---

## Contradiction Detection

A PostToolUse hook automatically checks new observations for conflicts with existing ones.

**How it works:**
1. After each tool call, the hook reads the latest observation from SQLite
2. Searches FTS5 for similar older observations (shared concepts)
3. Scores conflict likelihood based on: same type (esp. decisions), same files modified, contradiction signal words ("instead", "switch", "revert", etc.)
4. If score ≥ 3/7, inserts a `contradiction` type observation and alerts Claude

**Reviewing conflicts:**

```
/hybrid-search contradictions
```

This queries:
```sql
SELECT * FROM observations WHERE type = 'contradiction' ORDER BY created_at_epoch DESC LIMIT 10
```

For each contradiction, present the two conflicting observations and ask the user to:
- **Resolve:** Mark the contradiction as resolved (no action needed)
- **Supersede:** Mark the older observation as superseded (set `relevance_count = -1`)

Implementation: `~/.claude/skills/hybrid-search/contradiction_check.py`
Hook: `~/.claude/skills/hybrid-search/contradiction-check.sh` (rate-limited to 30s)

---

## 4-Tier Knowledge Consolidation

Knowledge automatically promotes through four tiers:

```
Tier 1: WORKING     → Raw per-tool observations (claude-mem default)
  ↓ claude-mem SessionEnd hook
Tier 2: EPISODIC    → Session summaries (claude-mem default)
  ↓ crystallize.sh (when concept count ≥ 5)
Tier 3: SEMANTIC    → Crystallized knowledge pages
  ↓ proceduralize.py (when action patterns repeat ≥ 3 times)
Tier 4: PROCEDURAL  → Reusable workflow recipes
```

### Tier 2→3: Auto-Crystallization

At session end, `crystallize.sh` finds concept clusters with ≥5 observations and distills them into structured markdown pages at `~/.claude-mem/crystallized/`.

Each crystal includes: Key Facts, Decisions, Bugs Fixed, Features, Files Involved, Action Patterns, and a Timeline.

Source observations are marked with `relevance_count = -1` (crystallized — safe to deprioritize in search since their value is captured in the crystal).

```
/hybrid-search crystals                   # list all crystals
/hybrid-search crystals "topic"           # read a specific crystal
```

To list, read `~/.claude-mem/crystallized/INDEX.md`.
To read a specific crystal, search the INDEX for matching topic, then read the file.

### Tier 3→4: Procedural Extraction

After crystallization, `proceduralize.py` scans crystal source observations for repeated action patterns: (type, concept) subsequences of length ≥3 that appear across ≥3 sessions.

Detected procedures are written as workflow templates at `~/.claude-mem/procedures/`.

```
/hybrid-search procedures                 # list all procedures
/hybrid-search procedures "topic"         # read a specific procedure
```

To list, read `~/.claude-mem/procedures/INDEX.md`.

### Force Promote

```
/hybrid-search promote
```

Runs the full pipeline immediately:
1. Execute `~/.claude/skills/hybrid-search/crystallize.sh`
2. Execute `python3 ~/.claude/skills/hybrid-search/proceduralize.py`
3. Report what was crystallized and what procedures were detected
