# Command: create

Generate BOTH a markdown document and a diagram on the same topic, linked via wiki-links. The document is the primary knowledge artifact -- comprehensive prose establishing concepts, structure, and relationships. The diagram supplements it as a visual overview, mapping the document's key concepts into layers and nodes.

**Key principle:** The document is the knowledge, the diagram is the map. The diagram gives "where am I" context as you read through the document.

## Usage

```
/knowledge-base create <topic>           # Generate both artifacts directly
/knowledge-base create <topic> -i        # Interactive mode: ask clarifying questions first
/knowledge-base create <topic> --interactive
```

## Inputs

The dispatcher passes:
- **topic** -- everything after the `create` token, with `-i`/`--interactive` stripped
- **interactive** -- boolean flag (`true` if `-i` or `--interactive` was present)
- **vaultRoot** -- absolute path to detected vault root (or `null` if no vault)
- **vaultConfig** -- parsed `.archdesigner/config.json` (or `null`)
- **gatheredContext** -- compound intelligence context block assembled by SKILL.md

## Naming Convention

Both files share the same topic slug:
- **Document:** `<topic-slug>.md` (e.g., `steam-engine.md`)
- **Diagram:** `<topic-slug>.json` (e.g., `steam-engine.json`)

They are linked together: the document contains a wiki-link to the diagram, and together they form a complete knowledge unit on the topic.

---

## Step 1: Parse Arguments

1. The **topic** string is the subject of both the document and diagram. It may be multiple words (e.g., `"Microservices authentication flow"`).
2. If the topic is empty, ask the user: "What topic should I create a document and diagram for?"
3. Check for the `-i` or `--interactive` flag. If present, set `interactive = true` and strip the flag from the topic string.
4. Derive a **topic-slug** via script — do not compute manually:

```bash
SLUG=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_utils.py slug "<topic>")
# If vault detected, check for duplicates:
SLUG=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_utils.py next-slug "$SLUG" "<vaultRoot>/memory/topic-registry.md")
```

## Step 1b: Suggest Placement

If `vaultRoot` is set, determine which collection (folder) this new topic belongs in before generating any content.

1. **Run the placement script**:

```bash
PLACEMENT=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_suggest_placement.py \
  --topic "<topic-slug>" \
  --vault-root "<vaultRoot>")
```

2. **Merge with graphify context**: From `gatheredContext`, identify the collection paths of the most semantically related existing topics (if graphify results are available).

3. **Present to the user** — combine the script's structural suggestion with any graphify semantic signal, then ask:

> **Where should this topic be placed?**
>
> Offer up to 4 options drawn from the script's `suggestions[]`, using their `display` and `reason` fields. Always include a "Vault root" option and an "Other (type path)" option.
>
> If the script suggests `react-next` with strong word overlap AND graphify confirms related topics are in `react-next/`, lead with that as the recommended option.

4. **Apply the confirmed path**: Set `topicFolder = "<vaultRoot>/<confirmed-path>/<topic-slug>/"` (create with `mkdir -p`). If the user picks "Vault root", use `<vaultRoot>/<topic-slug>/`. If the user types a custom path, use that directly (it may be nested, e.g. `react-next/nextjs-app-router/`).

5. **If no vault detected**: skip this step and use `<cwd>/<topic-slug>/` as the topic folder.

## Step 2: Detect Vault and Gather Context

The SKILL.md dispatcher handles vault detection and compound intelligence gathering before this command runs. Use the passed-in `vaultRoot`, `vaultConfig`, and `gatheredContext`.

Additionally, perform these create-specific context lookups:

### 2a. Archetype Preferences

If `vaultRoot` is set, check for `<vaultRoot>/memory/archetype-preferences.md`:

```bash
cat "<vaultRoot>/memory/archetype-preferences.md" 2>/dev/null
```

If it exists, read it for learned icon mappings, color choices, and layout preferences from prior diagram sessions and user corrections. These preferences override archetype defaults when they conflict.

### 2b. Topic Registry

If `vaultRoot` is set, check for `<vaultRoot>/memory/topic-registry.md`:

```bash
cat "<vaultRoot>/memory/topic-registry.md" 2>/dev/null
```

If it exists, scan for entries related to the current topic. This helps:
- Avoid duplicate topic slugs (append `-2`, `-3`, etc. if the slug already exists)
- Enable cross-referencing with existing content
- Detect related topics the user has worked on before

### 2c. Graphify -- Related Content

If `vaultRoot` is set and `gatheredContext` includes graphify results, extract:
- Existing **diagrams** (`.json` files) on related topics -- these can be wiki-linked from the document
- Existing **documents** (`.md` files) on adjacent topics -- these can be cross-referenced
- Structural clusters that include the topic's domain

### 2d. Claude-mem -- Past Work

From `gatheredContext`, extract:
- Past decisions or discoveries related to the topic
- User preferences for document structure, depth, or style
- Previous documents or diagrams generated on similar topics (to avoid redundancy)

### 2e. Vault MEMORY.md

If `vaultRoot` is set, check for `<vaultRoot>/.archdesigner/MEMORY.md`:

```bash
cat "<vaultRoot>/.archdesigner/MEMORY.md" 2>/dev/null
```

Look for feedback entries about:
- Preferred document depth (overview vs. deep-dive)
- Style preferences (academic, practical, tutorial-style)
- Structural conventions (e.g., always include a "Trade-offs" section)
- Diagram preferences (density, flow direction, color schemes)

## Step 3: Interactive Mode (if `-i` flag set)

If `interactive` is `true`, ask the user 2-3 targeted questions before generating. Tailor the questions based on the topic and any context gathered. Good defaults:

1. **Target audience**: "Who is the target audience? (e.g., senior engineers, beginners, decision-makers)"
2. **Depth level**: "What depth level? (e.g., executive overview, working knowledge, deep-dive reference)"
3. **Specific angles**: "Any specific angles or subtopics to emphasize? (e.g., trade-offs, security considerations, comparison with alternatives)"

Wait for the user's answers before proceeding to Step 4. Incorporate their answers into both the document and diagram generation.

If `interactive` is `false`, skip this step entirely and generate directly using the topic plus all gathered context.

## Step 4: Generate the Document FIRST

The document is the primary artifact. Generate it first so the diagram can be informed by its content.

Write a comprehensive, well-structured markdown document. This must be substantive prose, not a skeleton or template.

### Document Structure

```markdown
# <Topic Title>

Visual overview: [[<topic-slug>.json]]

<Opening paragraph: 1-3 sentences establishing what this topic is and why it matters.>

## <First Major Section>

<Substantive prose covering this aspect of the topic. Multiple paragraphs as needed.>

### <Subsection if warranted>

<More detailed content.>

## <Second Major Section>

...

## <Additional Sections as Needed>

...

## Related

- [[<topic-slug>.json]] -- Visual diagram of this topic
- [[wiki-link-to-related-doc]] -- (if related content exists in vault)
- [[wiki-link-to-related-diagram.json]] -- (if related diagrams exist in vault)
```

### Content Guidelines

1. **Title as H1** -- use the topic as-is or a slightly refined version
2. **Wiki-link to diagram near the top** -- immediately after the title or opening paragraph, include: `Visual overview: [[<topic-slug>.json]]`
3. **Sections with H2/H3 headings** -- organize logically for the topic domain
4. **Prose-first** -- write full paragraphs, not bullet-point outlines. Use lists only where they genuinely aid comprehension (e.g., listing concrete steps, enumerating options)
5. **Substantive** -- each section should teach or explain something. Avoid filler sentences and vague generalizations
6. **Contextual depth** -- if interactive mode provided a depth preference, honor it. Otherwise default to "working knowledge" level: enough for a practitioner to understand and apply
7. **Code examples** where relevant -- use fenced code blocks with language hints
8. **Cross-references** -- if related documents exist in the vault, include `[[other-doc]]` wiki-links in the body text or in the "Related" section at the end
9. **No YAML frontmatter** -- the document is plain markdown. Metadata is tracked in the topic registry, not in the file itself

### Section Selection Heuristics

Choose sections appropriate to the topic domain. Some common patterns:

| Topic Domain | Typical Sections |
|-------------|-----------------|
| Technology/tool | Overview, Core Concepts, How It Works, Use Cases, Trade-offs, Getting Started |
| Architecture pattern | Problem, Solution, Structure, Participants, When to Use, Limitations |
| Process/workflow | Overview, Prerequisites, Steps, Variations, Common Pitfalls |
| Comparison | Overview, Criteria, Option A, Option B, ..., Recommendation |
| Concept/theory | Definition, Background, Key Principles, Applications, Relationship to Other Concepts |

These are suggestions, not rigid templates. Adapt the structure to what serves the topic best.

### Output Location

All files for a topic (document, diagram, flow explanations) go into the topic folder determined in Step 1b:

- **If vault detected**: `topicFolder` is set in Step 1b (e.g., `<vaultRoot>/react-next/<topic-slug>/`)
- **If no vault detected**: `topicFolder` is `<cwd>/<topic-slug>/`

Create the folder with `mkdir -p "<topicFolder>"`. Write the document to `<topicFolder>/<topic-slug>.md`.

Before writing, check if the folder or document already exists:

```bash
ls "<topic-folder>/<topic-slug>.md" 2>/dev/null
```

If it exists, ask the user: "A document named `<topic-slug>.md` already exists in `<topic-slug>/`. Should I overwrite it, or use a different name?"

Write the document using the Write tool. Note the absolute folder path -- all remaining files go into this same folder.

## Step 5: Generate the Diagram SECOND

The diagram is informed by the document's content. It maps the key concepts, structure, and relationships from the document into a visual diagram with layers and nodes.

### 5a. Select Archetype

Run the archetype selection script — do not score archetypes manually:

```bash
ARCHETYPE_RESULT=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_archetype.py \
  --archetypes-dir ~/.claude/skills/knowledge-base/archetypes \
  --topic "<topic>")
```

- If output is `no-match`: adapt on the fly using `_archetype-template.md` as the structural guide (see diagram command Step 2c for full adaptation rules).
- Otherwise: output is `<archetype-name> <absolute-path-to-archetype.md>`. Read the full archetype file at the given path for all conventions (layers, icons, connections, layout, flows).

If `archetype-preferences.md` was loaded in Step 2a, apply any learned preferences that override archetype defaults (icon overrides, color preferences, layout preferences).

### 5b. Design Process

Execute these steps in order, informed by the document content from Step 4:

1. **Identify layers**: Group the document's key concepts by category/concern. Each group becomes a layer. Assign layer colors from the archetype or adaptation.

2. **List all nodes**: For each layer, enumerate the specific components/concepts from the document. Assign each:
   - `id`: `el-<short-descriptive-id>` (e.g., `el-browser`, `el-auth-svc`)
   - `label`: Human-readable name
   - `sub`: Optional subtitle or brief description
   - `icon`: From the archetype icon mappings or adapted mappings
   - `w`: Width in px (default 210, range 110-230)
   - `layer`: The layer ID this node belongs to

3. **Map connections**: Identify all relationships between nodes. Assign each:
   - `id`: `dl-<short-descriptive-id>`
   - `from` / `to`: Node IDs
   - `fromAnchor` / `toAnchor`: Anchor points
   - `color`: From the connection semantics
   - `label`: What flows along this connection
   - `labelPosition`: Adjusted per scenario to prevent overlaps (do NOT leave all at 0.5)

4. **Establish center axis**: Set x ~ 750. Design symmetric pairs and triads around this axis.

5. **Compute coordinates**: Start from y = 100. Apply spacing rules:
   - Same-row horizontal gap: 70px+ between node edges
   - Cross-layer vertical gap: 120-160px between node edges across adjacent layers
   - Layer boundary gap: 50-80px between layer boundaries
   - Within-layer padding: 25px inside layers around nodes
   - Layer title offset: 20px extra at top of each layer

6. **Verify all gaps**: Check every node-to-node and layer-to-layer gap meets minimums. Fix any violations before proceeding.

7. **Position condition nodes** (if any): Place between layers with sufficient gap. Condition nodes have `"shape": "condition"` and NO `layer` property. Verify no layer collisions.

8. **Adjust label positions**: Set `labelPosition` per scenario to prevent overlaps (condition outputs: 0.70, fan-outs: 0.60, long diagonals: 0.20-0.30, etc.).

9. **Assign colors**: Ensure each flow type uses a distinct color for visual tracing.

10. **Define flows**: Trace all meaningful end-to-end paths. Each flow:
    - Has an `id`: `flow-<descriptive-id>`
    - Has a `name`: Human-readable description of the path
    - Has `connectionIds`: Array of connection IDs forming a contiguous graph, listed in traversal order
    - Verify the contiguity constraint: each connection shares at least one node with another connection in the same flow
    - Draft a brief **flow explanation** (2–3 sentences) covering: trigger, key steps, outcome. Store for Step 5f.

### 5c. Diagram Title

The diagram title must match the document topic. Use the same title as the document's H1 heading.

### 5d. JSON Output

Produce the diagram as a JSON file conforming to the schema:

```json
{
  "title": "<Diagram Title>",
  "layers": [LayerDef],
  "nodes": [SerializedNodeData],
  "connections": [Connection],
  "layerManualSizes": {},
  "lineCurve": "bezier",
  "flows": [FlowDef],
  "documents": [DocumentMeta]
}
```

`DocumentMeta` entries are populated in Step 5f. If there are no flows, omit `documents`.

See the software-architecture archetype for the full schema of LayerDef, SerializedNodeData, Connection, and FlowDef.

### 5f. Flow Explanation Documents

For each flow defined in Step 5b, write a companion Markdown file in the same directory as the diagram. These are short "quick-reference" docs that surface in the Flow Properties panel when the user selects a flow — distinct from the comprehensive main document written in Step 4.

**Filename:** `<flow-descriptive-id>.md`, placed inside a `flow-descriptions/` subfolder: `<topicFolder>/flow-descriptions/<flow-descriptive-id>.md`

Create the subfolder first: `mkdir -p "<topicFolder>/flow-descriptions/"`

**Generate the tables via script** — after the diagram JSON has been written to disk:

```bash
TABLES=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_flow_tables.py \
  --diagram "<topic-folder>/<topic-slug>.json" \
  --flow "<flow-id>")
```

**Content template** — write only the prose paragraph; insert script output for the tables:

```markdown
# <Flow Name>

<The 2–3 sentence explanation drafted in Step 5b item 10: trigger, key steps, outcome.>

<TABLES — paste kb_flow_tables.py output here verbatim>

## Further Reading

For full context, see [[<topic-slug>.md]].
```

After writing each file, add a `DocumentMeta` entry to the `documents` array in the diagram JSON:

```json
{
  "id": "<topic-slug>-<flow-descriptive-id>",
  "filename": "<collection-path>/<topic-slug>/flow-descriptions/<flow-descriptive-id>.md",
  "title": "<Flow Name> — Explanation",
  "attachedTo": [{ "type": "flow", "id": "<flow-id>" }]
}
```

If a diagram has no flows, skip this step entirely.

### 5e. Output Location

Write the diagram JSON into the same topic folder created in Step 4: `<topic-folder>/<topic-slug>.json`.

Before writing, check if a file with the same name already exists:

```bash
ls "<topic-folder>/<topic-slug>.json" 2>/dev/null
```

If it exists, ask the user: "A diagram named `<topic-slug>.json` already exists. Should I overwrite it, or use a different name?"

Write the diagram JSON using the Write tool.

## Step 6: Update Vault State (if in vault)

Skip this entire step if no vault was detected (`vaultRoot` is `null`).

### 6a. Update Graphify

If graphify is available in the vault (check for `graphify-out/` or `.graphifyignore`), rebuild the index to include both new files:

```bash
cd "<vaultRoot>" && graphify . --update 2>/dev/null || true
```

If `graphify` is not on PATH, try the Python module:

```bash
cd "<vaultRoot>" && python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))" 2>/dev/null || true
```

If neither works, skip silently -- graphify update is best-effort.

### 6b. Note on Link Index

The `_links.json` wiki-link backlink index updates automatically when the vault is opened in Architecture Designer. No manual update is needed here. The `[[<topic-slug>.json]]` wiki-link in the document will be tracked automatically.

### 6c. Update Topic Registry

Ensure the `memory/` directory exists:

```bash
mkdir -p "<vaultRoot>/memory"
```

Run the registry script — do not append manually:

```bash
python3 ~/.claude/skills/knowledge-base/scripts/kb_utils.py append-registry \
  --vault-root "<vaultRoot>" \
  --date "<YYYY-MM-DD>" \
  --topic "<Topic>" \
  --slug "$SLUG" \
  --doc "<topic-slug>/<topic-slug>.md" \
  --diagram "<topic-slug>/<topic-slug>.json"
```

### 6d. Auto-Learn Archetype Preferences

Save any new or adapted conventions to `<vaultRoot>/memory/archetype-preferences.md`. Create the file (and `memory/` directory) if they don't exist.

**What to save:**

1. **Icon mappings used**: If the archetype was adapted on the fly (no match), save all icon choices so future diagrams in this domain reuse them.
2. **Color choices**: Save any custom layer colors or connection colors that were invented for a new domain.
3. **Layout decisions**: If a non-default flow direction was chosen, record it with the domain context.
4. **User corrections**: If during the session the user asks to change an icon, color, label, or layout choice, save the correction as a learned preference.

If the file already exists, merge new entries into the existing content. Do not duplicate entries -- if an identical mapping already exists, skip it.

## Report

After completing all steps, print a summary:

```
Created: <Topic>

  Document: <absolute-path-to-document>
    Sections: <count> sections
    Wiki-links: <count> cross-references included

  Diagram: <absolute-path-to-diagram>
    Archetype: <archetype-name or "adapted">
    Layers: <count>, Nodes: <count>, Connections: <count>, Flows: <count>
    Flow docs: <count> companion explanation documents pre-attached

  Vault: <vault-name> (or "none -- standalone files")
  Registry: <updated | created | skipped (no vault)>

Please open both files in the knowledge-base app and verify:
1. The document's [[<topic-slug>.json]] link opens the diagram
2. All diagram layers render with correct colors and titles
3. All nodes are positioned within their layers without overlap
4. All connections route cleanly between nodes
5. Labels are readable and don't overlap other elements
6. Each flow shows its companion explanation doc in the Flow Properties panel

If anything needs adjustment, describe the change and I'll update
both files and save the preference for future use.
```
