# Command: edit

Edit an existing diagram JSON file. All modifications MUST go through this command to ensure placement constraints are respected.

## Usage

```
/knowledge-base edit <path> [description of change]
```

- `<path>` — Path to an existing `.json` diagram file (absolute or relative to cwd).
- The description of what to change comes from the rest of the user's message or from interactive conversation.

## Inputs

- **path** (string, required): Path to the diagram JSON file.
- **change description** (string): What to add, remove, or modify.

## Step 1: Read and Parse

Read the diagram JSON at the given path. Extract:
- All `layers` with their IDs, titles, and colors
- All `nodes` (both regular and condition), their IDs, x, y, layer
- All `connections` with from/to/anchors
- All `flows` with their `connectionIds`
- `lineCurve` and `layerManualSizes`

## Step 2: Compute Layer Bounding Boxes

**All x, y coordinates are CENTER coordinates.** Before making any changes, compute the current bounding box of every layer.

For each layer, collect all nodes where `node.layer === layer.id`. For each node:
- `halfW = node.w / 2` (default w=210 → halfW=105)
- `halfH = node.w === 110 || node.w === 130 ? 30 : 35` (h=60 for narrow nodes, h=70 otherwise)
- `node_left = node.x − halfW`, `node_right = node.x + halfW`
- `node_top = node.y − halfH`, `node_bottom = node.y + halfH`

Layer bounds:
```
layer_left   = min(node_left)  − 25
layer_right  = max(node_right) + 25
layer_top    = min(node_top)   − 45   (25 padding + 20 title)
layer_bottom = max(node_bottom) + 25
```

Record these as `{ id, left, right, top, bottom }` for collision checks in later steps.

## Step 3: Plan the Change

Analyze the requested change. Categorize it:

| Change type | Key constraints |
|-------------|-----------------|
| Add regular node | Must assign a `layer`; x,y are center; use 70px+ horizontal gap between node edges |
| Add condition node | No `layer`; use `conditionSize`/`conditionOutCount`; must not overlap any layer (see Step 4) |
| Move node | Re-check layer membership if x,y change significantly |
| Add connection | Both `from` and `to` must be valid node IDs; anchor names must be valid |
| Remove connection | Check if any flow references this ID — update or remove affected flows |
| Add flow | All `connectionIds` must form a contiguous graph (each connection shares ≥1 node with another); also write a companion explanation document and add a `DocumentMeta` entry (see Step 7b) |
| Remove flow | Remove its `connectionIds` from any affected flows; also delete its companion doc file if one exists and remove it from `documents[]` (see Step 7b) |
| Edit label/icon/color | No spatial constraints — apply directly |
| Split a layer | Reassign `layer` field on affected nodes; recompute bounds for both new layers |

## Step 4: Condition Node Placement (if adding/moving a condition node)

Use the `conditionSize` and `conditionOutCount` fields — **never `size` or `exits`**.

### 4a. Compute condition dimensions

For `conditionSize=1, conditionOutCount=2`: w=81, h=70 (halfW=40.5, halfH=35).
For other sizes multiply by `1 + (conditionSize-1) * 0.25`.

### 4b. Choose a placement strategy

**Option A — Left of a layer** (when condition is at the same y level as a layer):

```
max_safe_x = min(node.x in target_layer) − 130 − halfCondW − 10
```

For a layer whose leftmost node center is at x=500 and conditionSize=1:
`max_safe_x = 500 − 130 − 40.5 − 10 = 319.5` → use x ≤ 319

**Option B — Between two layers** (condition bridges a vertical gap):

Required: `lower_layer_top − upper_layer_bottom > condH + 20` (≥ 90px for size=1)

```
safe_y_min = upper_layer_bottom + halfCondH + 10
safe_y_max = lower_layer_top   − halfCondH − 10
cond_y     = (safe_y_min + safe_y_max) / 2   (centered in gap)
```

If the x position is **within** either layer's x range, this y-gap rule applies. If x is outside both layers' x ranges entirely, no y constraint applies.

### 4c. Verify with rectsOverlap

For **every** layer, run the collision check:

```
x_overlap = (cond_x − halfCondW < layer_right + 10) AND (cond_x + halfCondW + 10 > layer_left)
y_overlap = (cond_y − halfCondH < layer_bottom + 10) AND (cond_y + halfCondH + 10 > layer_top)
collision  = x_overlap AND y_overlap
```

**Reject any position where `collision = true` for any layer.** Adjust x or y until all layers pass.

## Step 5: Validate Anchors

For any connection being added or modified, verify:
- **Regular node anchors**: `top-0`, `top-1`, `top-2`, `bottom-0`, `bottom-1`, `bottom-2`, `left-0`, `left-1`, `left-2`, `right-0`, `right-1`, `right-2`
- **Condition node anchors**: `cond-in` (entry), `cond-out-0` through `cond-out-N` (where N < `conditionOutCount`)

Never reference `cond-out-2` on a node with `conditionOutCount: 2` (valid exits are 0 and 1 only).

## Step 6: Validate Flow Contiguity

For any flow being added or that references modified connections:

Build a graph of `{ nodeId → set of connectionIds }` from the flow's `connectionIds`. The flow is contiguous if every connection can reach every other connection via shared nodes. 

Simple check: For each connection in the flow, at least one other connection in the same flow must share its `from` or `to` node ID.

If a connection is being removed: update every flow that contained it. If removal breaks contiguity, either remove the connection from the flow or remove the flow.

## Step 7: Apply and Write

### 7a. Update the JSON

Write the complete updated JSON back to the file. Preserve:
- All unmodified fields exactly as they were
- Key order: `title`, `layers`, `nodes`, `connections`, `layerManualSizes`, `lineCurve`, `flows`, `documents`
- 2-space indentation

### 7b. Sync flow explanation documents

After writing the JSON, handle companion explanation documents for any flow changes:

**If a flow was added:**

1. Write a companion `.md` file in the same directory as the diagram:
   - Filename: `<diagram-slug>-<flow-descriptive-id>.md`
   - Content: prose explanation of the flow (trigger, key steps, outcome), plus a Nodes Involved table and a Connections table (see `diagram.md` Step 3e for the template)

2. Add (or upsert) a `DocumentMeta` entry in the `documents[]` array of the JSON:
   ```json
   {
     "id": "<diagram-slug>-<flow-descriptive-id>",
     "filename": "<vault-relative path to the .md>",
     "title": "<Flow Name> — Explanation",
     "attachedTo": [{ "type": "flow", "id": "<flow-id>" }]
   }
   ```

**If a flow was removed:**

1. Find any entry in `documents[]` where `attachedTo` contains `{ "type": "flow", "id": "<removed-flow-id>" }`.
2. Remove that entry from `documents[]` in the JSON.
3. If the companion `.md` file exists on disk, delete it.

**If no flows were added or removed**, skip Step 7b entirely.

Then show the user a summary:

```
Updated: <filename>

Changes applied:
- [list each change made]

Please reload the diagram in the knowledge-base app and verify:
1. Any new/moved nodes appear within their layers (or free-floating for condition nodes)
2. Any new connections route cleanly
3. Flows highlight the intended paths
4. Any new flow shows its companion explanation doc in the Flow Properties panel
```

## Common Mistakes to Avoid

| Mistake | Correct approach |
|---------|-----------------|
| Using `size` field | Use `conditionSize` |
| Using `exits` field | Use `conditionOutCount` |
| Treating x,y as top-left | x,y are CENTER — node spans ±halfW, ±halfH |
| Placing condition at "the same x as the layer boundary" | Condition right+gap must be LESS THAN layer left |
| Skipping collision check | Run rectsOverlap against ALL layers, not just adjacent ones |
| Adding connection to flow without checking contiguity | Trace the graph — every pair must be reachable via shared nodes |
| Referencing `cond-out-2` on a 2-exit condition | Exits are 0-indexed: `cond-out-0`, `cond-out-1` only |
