# Command: diagram

Generate a diagram JSON file for any topic. Uses the archetype system to select visual conventions appropriate to the domain.

## Usage

```
/knowledge-base diagram <topic>
```

The `<topic>` is a free-form string describing what to diagram (e.g., "Kubernetes pod lifecycle", "TCP handshake", "photosynthesis process", "OAuth2 authorization code flow").

## Inputs

- **topic** (string, required): The subject of the diagram, passed from the SKILL.md dispatcher.
- **vault root** (string | null): The vault root path if vault detection succeeded, or null.
- **vault config** (object | null): Parsed `.archdesigner/config.json` if in a vault.
- **gathered context** (object): The compound intelligence context assembled by SKILL.md before dispatching.

## Step 0: Mandatory Graphify Pre-Check

Before doing anything else (before archetype selection, before structural planning, before any LLM generation), run the **Mandatory Graphify Pre-Check** defined in `SKILL.md` against `<topic>`. SKILL.md owns the protocol; do not re-implement it here.

Outcomes:
- **STRONG match found** → stop. Surface the matching paths to the user via the SKILL.md dialog ("Open / Edit / Generate-new-anyway?") and wait for their choice. Do not generate a duplicate diagram.
- **ADJACENT matches** → continue. Carry the matched paths in `gatheredContext.adjacentMatches`; weave them into the diagram's `documents.attached` list AND the "Related" section of the explanation doc you write in Step 4.
- **NONE** → continue.

The pre-check is skipped only when no vault is detected or no graphify index exists (SKILL.md emits the standard notice). Step 1c below still runs — it is a secondary, layout-oriented graphify query, not a duplicate of the pre-check.

## Step 1: Detect Vault and Gather Context

Vault detection is handled by SKILL.md before this command runs. Use the passed-in vault root and gathered context. Additionally, load vault-specific memory files:

### 1a. Archetype Preferences

If a vault is detected, check for `<vault-root>/memory/archetype-preferences.md`. If it exists, read it. This file contains learned icon mappings, color choices, and layout preferences from prior diagram sessions and user corrections. These preferences override archetype defaults when they conflict.

If the file does not exist, that is fine -- it will be created in Step 4.

### 1b. Topic Registry

If a vault is detected, check for `<vault-root>/memory/topic-registry.md`. If it exists, read it. This file lists all previously generated topics with their slugs, archetypes, and creation dates. Use this to:
- Avoid duplicate slugs (append `-2`, `-3`, etc. if the slug already exists)
- Detect related topics the user has diagrammed before (mention them if relevant)

### 1c. Additional Intelligence Queries

Beyond the context SKILL.md already gathered:
- Query graphify for the topic if a vault graph exists: look for related nodes, communities, and structural patterns that could inform the diagram layout.
- Query claude-mem for past diagram sessions: search for observations about prior diagrams, user corrections to layouts or icon choices, and archetype adaptations. Use MCP tool `mcp__plugin_claude-mem_mcp-search__search` with `query: "diagram <topic>"`.

## Step 1.5: Gather Sources

Sources are **mandatory** for skill-generated diagrams. Without them the user cannot verify what the diagram is grounded in.

1. **Top-level sources**: use WebSearch to find 2–4 canonical online resources for the topic. Prefer:
   - For protocols: the relevant RFC or W3C spec.
   - For algorithms: the original paper or its archive page.
   - For software architectures: the official documentation, an architectural blog post by the maintainers, or the source-code-of-record (e.g. GitHub repo).
   - Avoid: commercial blog posts that paraphrase canonical sources without adding insight.
2. **Per-entity sources** (encouraged when feasible): for any node / connection / flow whose concept has its own canonical source distinct from the top-level topic, search and attach. For nodes representing a specific service-or-protocol (e.g. an "OAuth Service" node), find that protocol's RFC.
3. **Record** the sources for use in Step 3b. Format each as:
   ```json
   { "url": "https://datatracker.ietf.org/doc/html/rfc6749", "title": "RFC 6749 — OAuth 2.0" }
   ```
4. **Minimum**: at least one top-level `sources` entry MUST be present in the final JSON. Per-entity sources are encouraged but not required.

## Step 2: Select Archetype

### 2a. Select Archetype via Script

Run the archetype selection script with `--output-type diagram` so meta-archetypes route to their `diagram.md` sub-archetype:

```bash
ARCHETYPE_RESULT=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_archetype.py \
  --archetypes-dir ~/.claude/skills/knowledge-base/archetypes \
  --topic "<topic>" \
  --output-type diagram)
```

Parse the 3-token output: `<name> <subtype> <path>`.
- `subtype` = `-` indicates a single-file archetype (e.g., `software-architecture`); use the `<path>` directly.
- `subtype` = `diagram` indicates a meta-archetype's diagram sub-archetype (e.g., `music`); the `<path>` points to the sub-archetype file.
- Output `no-match`: adapt on the fly using `_archetype-template.md` (see 2c below).

Read the archetype file at `<path>` for all conventions (layers, icons, connections, layout, flows). For meta sub-archetypes, also read `<meta-root>/manifest.json` for context (e.g., tradition badges, purpose-keywords).

### 2c. On-the-Fly Adaptation

When no archetype matches, create ad-hoc conventions using `_archetype-template.md` as the structural guide:

1. **Layer categories**: Invent 3-6 layer categories appropriate to the topic's domain. Each layer needs a purpose, background color (`#hex6`), and border color (`#hex6`). Use soft pastel backgrounds with matching stronger borders (follow the color pattern from the software-architecture archetype).

2. **Icon mappings**: Map the topic's concepts to Lucide icons from the available set listed in the archetype template. Choose icons by visual metaphor:
   - People/roles: `User`, `Users`
   - Data/storage: `Database`, `HardDrive`, `Archive`, `Folder`
   - Processing/compute: `Cpu`, `Cog`, `ServerCog`
   - Communication: `Mail`, `Bell`, `Radio`, `Wifi`
   - Security: `Shield`, `ShieldCheck`, `Lock`, `Key`, `Fingerprint`
   - Monitoring: `Activity`, `BarChart`, `Monitor`
   - External/cloud: `Cloud`, `CloudCog`, `Globe`
   - Code/config: `Code`, `FileCode`, `Terminal`, `GitBranch`
   - Networking: `Network`, `Router`, `Cable`, `Plug`
   - Generic containers: `Box`, `Container`, `Layers`, `Server`

3. **Connection colors**: Assign 3-6 distinct colors for different flow types in the diagram. Use the software-architecture connection palette as a starting point and adapt:
   - Primary flow: `#3b82f6` (blue)
   - Secondary/alternate: `#10b981` (green)
   - Decision/branch: `#f59e0b` (amber)
   - Data/resource: `#64748b` (slate)
   - Internal/logic: `#8b5cf6` (purple)
   - Error/exception: `#ef4444` (red)

4. **Layout preferences**: Apply universal spacing rules from the software-architecture archetype (these are app constants and apply to ALL diagrams regardless of domain). Choose flow direction based on topic nature:
   - Processes, pipelines, hierarchies: top-to-bottom
   - Timelines, sequences, workflows: left-to-right
   - Ecosystems, networks: radial (approximate with centered layout)

5. **Check archetype preferences**: If `archetype-preferences.md` was loaded in Step 1a, apply any learned preferences that are relevant (e.g., the user previously chose `Cpu` for "processor" in a hardware diagram -- reuse that mapping).

## Step 3: Generate the Diagram

Follow the design process defined in the selected archetype (or the adapted conventions from 2c). The software-architecture archetype's Design Process section is the canonical reference -- adapt it to the domain.

### 3a. Design Process

Execute these steps in order:

1. **Identify layers**: Group the topic's concepts by category/concern. Each group becomes a layer. Assign layer colors from the archetype or adaptation.

2. **List all nodes**: For each layer, enumerate the specific components/concepts. Assign each:
   - `id`: `el-<short-descriptive-id>` (e.g., `el-browser`, `el-auth-svc`, `el-ribosomes`)
   - `label`: Human-readable name
   - `sub`: Optional subtitle or brief description
   - `icon`: From the archetype icon mappings or adapted mappings
   - `w`: Width in px (default 210, range 110-230)
   - `layer`: The layer ID this node belongs to

3. **Map connections**: Identify all relationships between nodes. Assign each:
   - `id`: `dl-<short-descriptive-id>`
   - `from` / `to`: Node IDs
   - `fromAnchor` / `toAnchor`: Anchor points (see Anchor Points in software-architecture archetype)
   - `color`: From the connection semantics
   - `label`: What flows along this connection
   - `labelPosition`: Adjusted per the Label Positioning table (do NOT leave all at 0.5)

4. **Establish center axis**: Set x ~ 750. Design symmetric pairs and triads around this axis.

5. **Compute coordinates**: Start from y = 100. Apply spacing rules:
   - Same-row horizontal gap: 70px+ between node edges
   - Cross-layer vertical gap: 120-160px between node edges across adjacent layers
   - Layer boundary gap: 50-80px between layer boundaries
   - Within-layer padding: 25px inside layers around nodes
   - Layer title offset: 20px extra at top of each layer

6. **Verify all gaps**: Check every node-to-node and layer-to-layer gap meets minimums. Fix any violations before proceeding.

7. **Position condition nodes** (if any): Place between layers with sufficient gap. Condition nodes have `"shape": "condition"` and NO `layer` property. Verify no layer collisions using the formula from the archetype.

8. **Adjust label positions**: Set `labelPosition` per scenario to prevent overlaps (condition outputs: 0.70, fan-outs: 0.60, long diagonals: 0.20-0.30, etc.).

9. **Assign colors**: Ensure each flow type uses a distinct color for visual tracing.

10. **Define flows**: Trace all meaningful end-to-end paths. Each flow:
    - Has an `id`: `flow-<descriptive-id>`
    - Has a `name`: Human-readable description of the path
    - Has `connectionIds`: Array of connection IDs forming a contiguous graph, listed in traversal order
    - Verify the contiguity constraint: each connection shares at least one node with another connection in the same flow
    - Draft a brief **flow explanation** (3–5 sentences) covering: what triggers this flow, the key steps across nodes, and the outcome. Store this text for Step 3e.

#### Flow ordering, start, and end (optional but encouraged)

The new `FlowDef` shape supports three optional fields that turn a flow's connections into a numbered traversal:

```json
{
  "id": "flow-...",
  "name": "...",
  "connectionIds": [...],
  "category": "...",
  "nodeOrders": { "el-browser": 1, "el-api-gateway": 2, "el-auth-service": 3 },
  "startNodeIds": ["el-browser"],
  "endNodeIds": ["el-session-db"]
}
```

- **`nodeOrders`** — Map of node ID → integer step. Use when the flow has a well-defined sequence (request flows, OAuth grants, learning paths). Multiple nodes may share an order number to indicate parallel steps. Omit when ordering would mislead (highly branching state machines, freely-traversable architectures).
- **`startNodeIds`** — Array of node IDs that are valid entry points to the flow. For roadmaps, all "Foundations" topics are starts.
- **`endNodeIds`** — Array of node IDs that are valid exit points / outcomes.

For each generated flow, decide based on archetype:

| Archetype | Default behaviour |
|---|---|
| Roadmaps | Always emit. Lowest-stage topics → `startNodeIds`. Highest-stage topics → `endNodeIds`. `nodeOrders` reflects recommended traversal sequence. |
| Software architecture | Emit when the flow is a request lifecycle (e.g. login). Skip when the flow is a topology/relationship diagram. |
| Other | Emit when the diagram represents a process; skip otherwise. |

Validate after emission: every `nodeOrders` key, `startNodeIds` entry, and `endNodeIds` entry MUST appear as the `from` or `to` of at least one connection in the flow's `connectionIds`. If a candidate node ID does not satisfy this, drop it from the field rather than emit an unreachable reference.

### 3b. JSON Output

Produce the diagram as a JSON file conforming to the schema defined in the software-architecture archetype:

```json
{
  "title": "<Diagram Title>",
  "sources": [SourceLink],
  "layers": [LayerDef],
  "nodes": [SerializedNodeData],
  "connections": [Connection],
  "layerManualSizes": {},
  "lineCurve": "bezier",
  "flows": [FlowDef],
  "documents": [DocumentMeta]
}
```

`DocumentMeta` shape (one entry per companion document created in Step 3e):

```json
{
  "id": "<uuid-or-slug>",
  "filename": "<vault-relative-path-to-.md>",
  "title": "<flow name> — Explanation",
  "attachedTo": [{ "type": "flow", "id": "<flow-id>" }]
}
```

The `documents` array tells the app which documents are pre-attached to which flows. When the user opens the diagram, attachments are restored automatically. **Only include entries for documents that were actually written to disk in Step 3e.**

`SourceLink` shape (one per entry in any `sources` array):

```json
{
  "url": "https://example.com/...",
  "title": "Optional display label"
}
```

Notes:
- Omit `title` rather than emit `""` — the app falls back to the URL host when `title` is absent.
- Per-entity sources nest the same shape inside any `LayerDef`, `SerializedNodeData`, `Connection`, or `FlowDef` (each accepts an optional `sources` array).

`FlowDef` shape (one entry per flow in the `flows` array):

```json
{
  "id": "flow-<descriptive-short-id>",
  "name": "Human Readable Flow Name",
  "category": "Optional Category",
  "connectionIds": ["dl-conn1", "dl-conn2", "dl-conn3"],
  "sources": [SourceLink],
  "nodeOrders": { "<node-id>": 1 },
  "startNodeIds": ["<node-id>"],
  "endNodeIds": ["<node-id>"]
}
```

- `nodeOrders` — optional map of node ID → integer traversal step (see Step 3a "Flow ordering, start, and end").
- `startNodeIds` — optional array of node IDs that are valid entry points to the flow.
- `endNodeIds` — optional array of node IDs that are valid exit points / outcomes.

See the software-architecture archetype for the full schema of LayerDef, SerializedNodeData, Connection, and FlowDef.

### 3e. Flow primary documents (and optional extension docs)

For each flow defined in Step 3a, write a **rich primary document** that explains the flow as a self-contained piece of writing — not a hub, not a stub. The 3–5 sentence + table format used previously is **deprecated**.

#### 3e.1 Primary doc

1. **Filename**: `<topicFolder>/flow-descriptions/<flow-id>.md`. Create the folder with `mkdir -p` first.

2. **Length**: aim for 1500–3000 words. Do not pad — if the flow honestly fits in 800 words, write 800. Padding hurts skim-readability.

3. **Structure** (adaptive — let the topic shape the headings, not a rigid taxonomy):
   - **Overview** — one-paragraph summary of the trigger, the path, and the outcome.
   - **What happens** — narrative pass through the nodes in flow order. For each node, name it, explain its role in this flow, link to its detailed page or RFC.
   - **Why this grouping** — why these nodes and connections form a coherent flow (and what's intentionally not in it).
   - **How connections work** — for each non-trivial connection, explain the protocol, the contract, the failure mode.
   - **Edge cases** — at least one paragraph on what happens when the flow doesn't go cleanly (timeouts, errors, partial state).
   - **Cross-references** — wiki-links to related diagrams, related flows, related concept documents.

4. **Wiki-links**:
   - Use `[[other-doc.md]]` to link to other vault documents.
   - Use `[[other-doc.md#header]]` when linking to a specific section.
   - Use `[[other-diagram.json]]` to link to other diagrams.

5. **Auto-generated tables**:
   - Run `kb_flow_tables.py` as before, but embed the output as an appendix at the end (under "## Appendix: Connection reference") rather than as the body. The table is a reference; the prose is the document.

6. **Sources**: copy the flow's `sources` (if any) and the relevant top-level diagram sources into a YAML frontmatter block:

   ```markdown
   ---
   sources:
     - url: https://datatracker.ietf.org/doc/html/rfc6749
       title: RFC 6749 — OAuth 2.0
   ---

   # Flow Name

   ...
   ```

   Use **block-list syntax only** for `sources:` (each entry on its own line, prefixed with `- url:`). Inline form (`sources: [{...}]`) is silently treated as an unknown key by the app's frontmatter parser and the field will not surface in the document properties panel.

#### 3e.2 Extension docs (conservative, optional)

While drafting the primary, identify any subtopic that:

- Naturally takes 400+ words to explain at appropriate depth.
- Has its own canonical source distinct from the parent flow.
- Would dilute the primary if kept inline.

For each such subtopic, generate a sibling extension doc:

- **Filename**: `<topicFolder>/flow-descriptions/<flow-id>/<subtopic-slug>.md`. Create the subfolder with `mkdir -p` first.
- **Self-contained**: the extension is its own document, not a continuation. It MAY assume the reader has read the primary, but should re-state context briefly.
- **Wiki-link from primary**: at the relevant section of the primary, insert `[[<flow-id>/<subtopic-slug>.md#overview]]` (anchor optional).
- **No registration**: only the primary doc is registered in the diagram's `documents[]`. The extension is reachable through wiki-links + the auto-derived backlinks.
- **Conservative bias**: when in doubt, keep the content inline rather than spawn an extension. Truly deeper dives belong in a fresh `/kb document` or `/kb create` session.
- **Interactive mode (`-i`)**: surface borderline candidates to the user and ask before writing.

#### 3e.3 Registration

Append a `DocumentMeta` to the diagram JSON's `documents` array for each primary doc:

```json
{
  "id": "<topic-slug>-<flow-id>",
  "filename": "<collection-path>/<topic-slug>/flow-descriptions/<flow-id>.md",
  "title": "<Flow Name>",
  "attachedTo": [{ "type": "flow", "id": "<flow-id>" }]
}
```

Extension docs are NOT registered. If a diagram has no flows, skip this step (the `documents` key may be omitted from the JSON).

### 3c. Output Location

Use the `topicFolder` confirmed in the placement step (Step 1d below). Write the JSON to `<topicFolder>/<topic-slug>.json`. Flow explanation documents go into `<topicFolder>/flow-descriptions/`.

Create folders with `mkdir -p` before writing.

### 3d. Topic Slug

Run the slug script — do not compute this manually:

```bash
SLUG=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_utils.py slug "<topic>")
```

If a vault is detected and a registry exists, check for duplicates:

```bash
SLUG=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_utils.py next-slug "$SLUG" "<vault-root>/memory/topic-registry.md")
```

### 1d. Suggest Placement

After deriving the slug, if `vaultRoot` is set:

1. **Run the placement script**:

```bash
PLACEMENT=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_suggest_placement.py \
  --topic "<topic-slug>" \
  --vault-root "<vault-root>")
```

2. **Merge with graphify context**: From `gatheredContext`, identify the collection paths of the most semantically related existing topics.

3. **Present to the user** — ask which collection this diagram belongs in. Offer up to 4 options from the script's `suggestions[]` (using `display` and `reason` fields), plus "Vault root" and "Other (type path)".

4. **Apply the confirmed path**: `topicFolder = "<vault-root>/<confirmed-path>/<topic-slug>/"`. If user picks "Vault root", use `<vault-root>/<topic-slug>/`. Custom paths (e.g. `react-next/nextjs-app-router/`) are supported.

5. **If no vault detected**: skip and use `topicFolder = <cwd>/<topic-slug>/`.

## Step 4: Update Vault State

Skip this entire step if no vault was detected.

### 4a. Update graphify

If graphify is available in the vault, run an incremental rebuild to index the new diagram:

```bash
cd <vault-root> && graphify . --update
```

If graphify is not installed or the command fails, skip silently -- this is a best-effort enhancement.

### 4b. Update Topic Registry

Run the registry script — do not append manually:

```bash
python3 ~/.claude/skills/knowledge-base/scripts/kb_utils.py append-registry \
  --vault-root "<vault-root>" \
  --date "<YYYY-MM-DD>" \
  --topic "<topic>" \
  --slug "$SLUG" \
  --diagram "<topic-slug>/<topic-slug>.json"
```

### 4c. Auto-Learn Archetype Preferences

Save any new or adapted conventions to `<vault-root>/memory/archetype-preferences.md`. Create the file (and `memory/` directory) if they don't exist.

**What to save:**

1. **Icon mappings used**: If the archetype was adapted on the fly (no match), save all icon choices so future diagrams in this domain reuse them.
2. **Color choices**: Save any custom layer colors or connection colors that were invented for a new domain.
3. **Layout decisions**: If a non-default flow direction was chosen, record it with the domain context.
4. **User corrections**: If during the session the user asks to change an icon, color, label, or layout choice, save the correction as a learned preference.

**Format of archetype-preferences.md:**

```markdown
# Archetype Preferences

Learned preferences from past diagram sessions. These override archetype defaults.

## Icon Overrides

| Domain | Concept | Icon | Learned From |
|--------|---------|------|-------------|
| <domain> | <concept> | <icon> | <topic> (<date>) |

## Color Preferences

| Domain | Flow Type | Color | Learned From |
|--------|-----------|-------|-------------|
| <domain> | <flow-type> | <color> | <topic> (<date>) |

## Layout Preferences

| Domain | Setting | Value | Learned From |
|--------|---------|-------|-------------|
| <domain> | <setting> | <value> | <topic> (<date>) |
```

If the file already exists, merge new entries into the existing tables. Do not duplicate entries -- if an identical mapping already exists, skip it.

### 4d. Auto-Learn from User Corrections

If the user requests changes to the generated diagram during the session (e.g., "change the database icon to HardDrive", "make the auth connections red instead of green", "move the API gateway to the left"), apply the change to the JSON file AND save the preference to `archetype-preferences.md` so future diagrams benefit from the correction.

When saving a correction, record:
- The original choice and the user's preferred choice
- The domain context so it applies to similar future topics
- The date for freshness tracking

## Step 5: Verification

After writing the JSON file, present the user with a verification checklist and tell them to load the diagram in the knowledge-base app:

```
Diagram generated: <filename>.json
Location: <full-path>

Please open this file in the knowledge-base app and verify:

1. All layers render with correct colors and titles
2. All nodes are positioned within their layers without overlap
3. All connections route cleanly between nodes
4. Labels are readable and don't overlap other elements
5. All flows are listed in the Architecture Properties panel
6. Selecting a flow correctly highlights the intended path
7. Each flow has a companion primary document at `flow-descriptions/<flow-id>.md` registered in the diagram's `documents[]` and pre-attached to the flow. Optional extensions, if any, are wiki-linked from the primary.

If anything needs adjustment, describe the change and I'll update
the diagram and save the preference for future use.
```

If in a vault, also mention:
```
Vault updated:
- Topic registered in memory/topic-registry.md
- Preferences saved to memory/archetype-preferences.md
- graphify index updated (if available)
```
