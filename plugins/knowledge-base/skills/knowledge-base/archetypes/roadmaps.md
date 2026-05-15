---
name: roadmaps
description: Learning roadmaps and skill trees in the roadmap.sh visual style — topics organized as a directed acyclic graph with prerequisites, required/optional marks, and progressive learning paths
domain-indicators:
  - roadmap
  - learning path
  - skill tree
  - curriculum
  - syllabus
  - study plan
  - learn
  - master
  - become
  - guide to
  - path to
  - prerequisites
  - tutorial
  - course
  - bootcamp
  - career
  - junior
  - senior
  - mentor
  - apprentice
  - skills
  - competency
  - mastery
  - fundamentals
  - basics
  - advanced
  - specialization
---

# Archetype: Roadmaps

Visual conventions for **learning roadmaps**, **skill trees**, and **curriculum diagrams** — modelled after roadmap.sh. A roadmap shows topics arranged in stages, the prerequisites between them, and which path a learner should follow to reach a goal.

The reader scans top-to-bottom: foundations first, then progressively more advanced topics. Required topics form the spine; optional topics branch off. Status (`Required` / `Recommended` / `Optional` / `Alternative`) is encoded in the node's `sub` field; the prerequisite chain is encoded as connections.

## JSON Schema

The diagram output is a JSON file. The output location is determined by the `/knowledge-base diagram` command based on vault detection (vault root or cwd).

### Top-Level Structure

```json
{
  "title": "string",
  "layers": [LayerDef],
  "nodes": [SerializedNodeData],
  "connections": [Connection],
  "layerManualSizes": {},
  "lineCurve": "bezier",
  "flows": [FlowDef]
}
```

`lineCurve` — for roadmaps prefer `"bezier"` (smooth prerequisite curves) or `"orthogonal"` (clean right-angle paths through dense skill trees). Pick one and keep it consistent within a roadmap.

### LayerDef

```json
{
  "id": "ly-<short-id>",
  "title": "STAGE TITLE IN UPPERCASE",
  "bg": "#hex6",
  "border": "#hex6"
}
```

### SerializedNodeData

```json
{
  "id": "el-<short-id>",
  "label": "Topic Name",
  "sub": "Required | Recommended | Optional | Alternative",
  "icon": "IconName",
  "x": 450,
  "y": 100,
  "w": 210,
  "layer": "ly-<layer-id>"
}
```

The `sub` field is **load-bearing** in roadmaps. It must be one of the four status labels above:

- **Required** — must be learned to progress; on the critical path
- **Recommended** — strongly suggested but not strictly blocking
- **Optional** — nice-to-have, broadens knowledge
- **Alternative** — substitute for another node (e.g., "Vue" as alternative to "React")

Use `condition` shape (`"shape": "condition"`) for **decision points** in the curriculum (e.g., "Choose a framework" with React / Vue / Svelte branching out). Condition nodes have NO `layer` property — see software-architecture archetype for full condition schema.

### Connection

```json
{
  "id": "dl-<short-id>",
  "from": "el-<source-id>",
  "to": "el-<target-id>",
  "fromAnchor": "bottom-1",
  "toAnchor": "top-1",
  "color": "#hex6",
  "label": "",
  "labelPosition": 0.5,
  "connectionType": "synchronous"
}
```

For roadmaps, most connections are unlabeled — the prerequisite arrow itself carries the meaning. Only label connections when the relationship is non-obvious (e.g., `"unlocks"`, `"deepens"`, `"or"`). Use `connectionType: "asynchronous"` (dashed line) for **optional / alternative** prerequisites.

### FlowDef

Roadmap flows represent **learning paths** — orderings through the topics. A typical roadmap defines 2–4 flows:

```json
{
  "id": "flow-fullstack-path",
  "name": "Full-Stack Web Path",
  "category": "Learning Paths",
  "connectionIds": ["dl-html-css", "dl-css-js", "dl-js-react", "dl-js-node", "dl-react-deploy", "dl-node-deploy"],
  "nodeOrders": {
    "el-html": 1, "el-css": 1,
    "el-js": 2,
    "el-react": 3, "el-node": 3,
    "el-deploy": 4
  },
  "startNodeIds": ["el-html", "el-css"],
  "endNodeIds": ["el-deploy"]
}
```

In this example, **HTML and CSS are co-equal starting points** — both have `nodeOrders` value `1` and both appear in `startNodeIds`, signalling that a learner can begin with either (or both in parallel). **JavaScript** is order `2` — the single bridge between foundations and frameworks. **React and Node** are **parallel mid-path topics**, both at order `3`, reflecting that a full-stack learner picks them up in either order. **Deploy** is the single end at order `4`, listed in `endNodeIds`. For "choose-your-path" roadmaps where learners specialise (e.g., frontend specialist, backend specialist, mobile specialist), it is common to have multiple ends — name several specialisations as `endNodeIds` so each terminal topic shows as a valid finish line.

A second, deliberately **minimal** companion — the `flow-minimum-path` shape that a fresh roadmap should always start with — looks like this:

```json
{
  "id": "flow-minimum-path",
  "name": "Minimum Path",
  "category": "Learning Paths",
  "connectionIds": ["dl-html-css", "dl-css-js", "dl-js-deploy"],
  "nodeOrders": {
    "el-html": 1,
    "el-css": 2,
    "el-js": 3,
    "el-deploy": 4
  },
  "startNodeIds": ["el-html"],
  "endNodeIds": ["el-deploy"]
}
```

The minimum path is intentionally linear — one start, one end, no branches — and represents the "what's the bare minimum I need to know?" answer. Always author this flow first; richer paths (`flow-fullstack-path` above, `flow-specialist-path`, etc.) are layered on top.

**Recommended flows for any roadmap:**

| Flow | Purpose |
|------|---------|
| `flow-minimum-path` | The shortest required-only path to be employable / functional |
| `flow-recommended-path` | The well-rounded, conventional path most learners should take |
| `flow-specialist-path` | A deeper, narrower path toward a specialization (frontend → animation, backend → distributed systems) |
| `flow-fast-track` | An accelerated path for experienced learners coming from an adjacent field |

Contiguity rule applies — every connection in a flow must share a node with another connection in the same flow.

## Layer Conventions

Roadmaps are organised into **stages** of learning. Pick 4–7 stages appropriate to the domain. Stage names should describe progression (Foundations → Mastery), not categories (Frontend, Backend, etc. — those go in node sub-fields or as separate roadmaps).

| Stage | Purpose | Background | Border |
|-------|---------|------------|--------|
| Prerequisites | Skills the learner must already have | `#f1f5f9` | `#cbd5e1` |
| Foundations | The minimum vocabulary; absolute basics | `#fef3c7` | `#fcd34d` |
| Core Skills | The day-to-day working knowledge | `#fef9c3` | `#fde047` |
| Frameworks / Tooling | Common tools, libraries, ecosystems | `#eff6ff` | `#bfdbfe` |
| Practice | Hands-on application; projects, exercises | `#ecfdf5` | `#6ee7b7` |
| Advanced | Beyond working knowledge; depth and nuance | `#f5f3ff` | `#c4b5fd` |
| Specialization | Narrow expertise paths | `#fdf2f8` | `#f9a8d4` |
| Mastery | Teaching-level understanding | `#fff1f2` | `#fecdd3` |

Yellow tones (`#fef3c7`/`#fef9c3`) for early stages echo roadmap.sh's primary palette; cooler tones for later stages signal progression. Stages further down the roadmap should use cooler colors to visually communicate "deeper" knowledge.

## Icon Mappings

**Only these 41 icons are registered in the app.** Any other icon name silently renders as `Database`. Do not use icon names outside this list — not even common Lucide icons like `BookOpen`, `Lightbulb`, `Trophy`, `Star`, or `GraduationCap`.

Registered: `Activity`, `Archive`, `BarChart`, `Bell`, `Box`, `Cable`, `Cloud`, `CloudCog`, `Code`, `Cog`, `Container`, `Cpu`, `Database`, `DatabaseZap`, `FileCode`, `Fingerprint`, `Folder`, `GitBranch`, `Globe`, `HardDrive`, `Key`, `Laptop`, `Layers`, `Lock`, `Mail`, `Monitor`, `Network`, `Plug`, `Radio`, `Router`, `Server`, `ServerCog`, `Shield`, `ShieldCheck`, `Smartphone`, `Tablet`, `Terminal`, `User`, `Users`, `Wifi`, `Zap`.

| Concept | Icon | Notes |
|---------|------|-------|
| A topic / concept (default) | `Layers` | The generic topic node — use when nothing more specific fits |
| A language / framework | `Code` | Programming languages, frameworks, syntax-heavy topics |
| A specific tool / library | `FileCode` | Named library, framework, or config-driven tool |
| A command-line tool | `Terminal` | CLI, shell scripting, terminal-based work |
| A protocol / standard | `Network` | HTTP, TCP, RFCs, web standards |
| Source control | `GitBranch` | Git, GitHub, version control concepts |
| A data / storage topic | `Database` | SQL, NoSQL, data modelling |
| A high-performance topic | `DatabaseZap` | Caching, real-time data, optimisation |
| A cache / speed topic | `Zap` | Caching, performance, speed |
| A cloud / hosting topic | `Cloud` | AWS, GCP, Azure, hosting |
| A configurable cloud topic | `CloudCog` | Cloud configuration, IaC, ops |
| A web / browser topic | `Globe` | Web platform, browser APIs, internet |
| Mobile platform | `Smartphone` | iOS, Android, mobile-specific |
| Tablet platform | `Tablet` | Tablet UX, large-screen mobile |
| Desktop platform | `Laptop` | Desktop apps, OS-specific |
| Monitor / dashboard | `Monitor` | Admin UIs, dashboards, observability views |
| Server-side topic | `Server` | Backend services, server-side rendering |
| Server with config | `ServerCog` | DevOps, server configuration, deployment |
| Container / virtualization | `Container` | Docker, Kubernetes, containerization |
| CPU / systems topic | `Cpu` | Low-level systems, OS, compilers |
| Authentication topic | `Key` | Login, OAuth, JWT, credentials |
| Identity / biometrics | `Fingerprint` | Identity providers, SSO |
| Security / hardening | `Shield` | Security best practices, defensive programming |
| Verified security | `ShieldCheck` | TLS, certificates, security audits |
| Encryption | `Lock` | Cryptography, encryption, secure protocols |
| User / persona topic | `User` | UX, user research, single-user concepts |
| Team / collaboration | `Users` | Team workflows, code review, soft skills |
| Configuration / settings | `Cog` | Config files, environment, settings management |
| Plugin / integration | `Plug` | Plugins, extensions, integrations |
| Layered / abstraction | `Layers` | Abstraction layers, architecture concepts |
| File / folder topic | `Folder` | File system, project structure |
| Package / artifact | `Box` | Package managers, registries, artifacts |
| Email / notifications | `Mail` | Email systems, notification design |
| Alerting | `Bell` | Alerts, push, real-time messaging |
| Activity / metrics | `Activity` | Monitoring, metrics, observability |
| Analytics / charts | `BarChart` | Analytics, BI, data visualization |
| Archive / persistence | `Archive` | Long-term storage, backup |
| Wiring / direct connection | `Cable` | Low-level networking, direct integration |
| Routing / load balancing | `Router` | API gateways, routing topics |
| Wireless | `Wifi` | Wireless protocols, networking |
| Broadcast / pub-sub | `Radio` | Event systems, broadcasting, message buses |
| Hard drive / file storage | `HardDrive` | Disk, file storage, persistent storage |

### Picking icons quickly

When in doubt:
- A specific named technology (e.g., "React", "Postgres", "Docker") → use the most specific match (`Code`, `Database`, `Container`)
- A general concept (e.g., "Async programming", "Big-O") → `Layers`
- A skill-of-doing (e.g., "Code review", "Pair programming") → `Users`
- A theory/foundation topic (e.g., "Type theory", "OS internals") → `Cpu`

## Connection Semantics

Roadmap connections express **prerequisite relationships** — "before X you should know Y". Use line color to signal how strict that relationship is.

| Relationship | Color | Line Style | Meaning |
|--------------|-------|------------|---------|
| Required prerequisite | `#3b82f6` (blue) | solid | "Must know before progressing" — the spine of the roadmap |
| Recommended prerequisite | `#10b981` (green) | solid | "Strongly suggested" — most learners follow this edge |
| Optional / enriching | `#8b5cf6` (purple) | dashed | "Deepens understanding but skippable" — branch path |
| Alternative path | `#f59e0b` (amber) | dashed | "Or this instead" — pick-one decision branches |
| Unlocks specialisation | `#ec4899` (pink) | solid | "Once you know X, you can pursue Y" — gateway to advanced |
| Practice / project link | `#64748b` (slate) | solid | "Apply what you learned" — links theory to a hands-on node |

Use `connectionType: "asynchronous"` for the **dashed** line styles (Optional, Alternative). Use `connectionType: "synchronous"` for solid lines.

## Layout Preferences

- **Primary direction:** top-to-bottom. Earlier stages at top, mastery at bottom.
- **Center axis:** x ~ 750. The "spine" of required topics runs down this axis. Optional topics branch left and right.
- **Density:** moderate-to-dense. Roadmaps typically have many small nodes (15–40 topics is typical).
- **Symmetry:** required-only spine on center axis; optional/alternative branches mirror left and right where possible.
- **Reading flow:** the eye should be able to trace a learning path top-to-bottom without backtracking.

### Anchor Points

Each node has 12 anchor points (3 per side):

| Side | Positions (at 25%, 50%, 75% of edge) |
|------|--------------------------------------|
| Top | `top-0`, `top-1`, `top-2` |
| Bottom | `bottom-0`, `bottom-1`, `bottom-2` |
| Left | `left-0`, `left-1`, `left-2` |
| Right | `right-0`, `right-1`, `right-2` |

For roadmap connections:
- **Vertical prerequisites (same column)**: `bottom-1` → `top-1`
- **Branching to optional siblings**: `right-1` → `left-1` (or mirror)
- **Skip-ahead / cross-stage**: `right-2` → `left-0` (long diagonal)

## Critical Spacing Rules

These rules prevent node collisions and keep the prerequisite arrows readable. Same constants as software-architecture; reproduced here for self-contained reference.

### Node Dimensions

- **Default width**: 210px (range: 110–230px). Use 110–140 for short topic labels (e.g., "HTML", "Git") to fit more nodes per row.
- **Node height**: 70px for w ≥ 140, 60px for w = 110 or 130.

### Minimum Gaps

- `NODE_GAP` = 8px minimum between nodes; use **70px+** for connection routing room
- `LAYER_GAP` = 10px minimum between layer boundaries; use **60–80px** for visual clarity
- `LAYER_PADDING` = 25px inside layers around nodes
- `LAYER_TITLE_OFFSET` = 20px extra at top of layer for the stage title

### Center Coordinate System

All `x`, `y` values in the JSON are the **center** of the node bounding box. A node at `x: 750, y: 100` with `w: 210, h: 70` spans `x: 645–855, y: 65–135`.

### Roadmap-Specific Layout Recipe

A typical 5-stage roadmap with 25 topics:

1. **Stage 1 (Prerequisites)**: 1–3 topics centered around x=750, y=120
2. **Stage 2 (Foundations)**: 3–5 topics in a row at y=280
3. **Stage 3 (Core Skills)**: 5–8 topics in 1–2 rows at y=440 / y=540
4. **Stage 4 (Frameworks/Tooling)**: 4–6 topics with clear left/right branches off the spine at y=700
5. **Stage 5 (Specialisation)**: 3–5 leaf nodes at y=900

Reserve x=750 ± 130 for the **required spine**. Place `Optional` and `Alternative` nodes at x ≤ 540 (left branch) or x ≥ 960 (right branch).

## Required-Spine Pattern

The single most important visual technique for roadmaps:

1. Identify all **Required** topics (the critical path).
2. Place them all at x=750 (center axis).
3. Connect them top-to-bottom with **blue solid** connections (`#3b82f6`, synchronous).
4. Place **Recommended** topics on either side, slightly offset (e.g., x=540 left, x=960 right), and connect to the nearest required node with **green solid** connections.
5. Place **Optional** topics further out (x ≤ 380 or x ≥ 1120) and connect with **purple dashed** connections (`#8b5cf6`, asynchronous).
6. Place **Alternative** clusters using a `condition` node as the decision point; connect with **amber dashed** connections.

The result: a visually obvious spine of required topics with optional knowledge branching out.

## Connection Label Positioning

Most roadmap connections are unlabeled. When a label is needed:

| Scenario | labelPosition | Rationale |
|----------|--------------|-----------|
| Decision branches (condition outputs) | **0.70** | Push label toward target choice, away from diamond |
| Long diagonals (cross-stage) | **0.20–0.30** | Keep label near source so it doesn't crowd the destination cluster |
| Short branches off the spine | **0.50** | Midpoint is fine for short connections |
| Optional/dashed enrichment lines | **0.65** | Slight bias toward target so the dashed pattern reads from source to enrichment |

## Flow Design Guidelines

1. **Always define `flow-minimum-path`** — the absolute shortest required-only route. This is the answer to "what's the bare minimum I need to know?"
2. **Always define `flow-recommended-path`** — the conventional path most learners take. Includes recommended, may skip optional.
3. **Define a specialization flow per branch** — e.g., on a frontend roadmap, define `flow-animation-specialist`, `flow-accessibility-specialist`.
4. **Name flows in the form `<adjective> <noun> path`** — "Minimum Viable Path", "Recommended Frontend Path", "Animation Specialist Path".
5. **Verify contiguity** — every connection in a flow must share a node with at least one other connection in the same flow.

### Categories

Use `category: "Learning Paths"` for all roadmap flows so they group together in the properties panel. If a roadmap has both learner-paths and reference-paths (e.g., "Quick reference for X"), use a second category.

## Design Process

1. **Define the goal**. What does someone reach by completing this roadmap? Be concrete — "Become a junior frontend dev" beats "Learn frontend".
2. **Identify the stages** (4–7 layers). Use progression names (Foundations → Mastery), not categories.
3. **List all topics** for each stage. Mark each as Required / Recommended / Optional / Alternative.
4. **Identify decision points** (e.g., "pick a framework"). Model these as `condition` nodes.
5. **Map prerequisites** between topics. Required-to-required connections are the spine; everything else branches off.
6. **Layout the spine** at x=750, top-to-bottom. Add 120–160px between stage rows.
7. **Place branches** on either side. Closer to the spine = more recommended; further = more optional.
8. **Pick connection colors** per the Connection Semantics table. Use `asynchronous` connection type for dashed lines.
9. **Define flows** — at minimum, `flow-minimum-path` and `flow-recommended-path`.
10. **Verify**: every Required topic is reachable from the start by following blue connections; the spine is at x=750; branches don't overlap stage boundaries.

## Verification Checklist

After creating the JSON, load it in the app to verify:

1. All stages render with correct colors and titles, in the correct top-to-bottom order
2. Required topics form a clear vertical spine at x=750
3. Optional topics are visually distinguishable (dashed lines, side branches)
4. Every node has a `sub` field set to one of: Required, Recommended, Optional, Alternative
5. The minimum-path flow highlights only the spine when selected
6. The recommended-path flow includes most of the diagram when selected
7. No node icon falls outside the 41 registered icons (silent fallback to `Database` is a bug)
8. Decision points (where present) render as diamonds and have correct `conditionOutCount`
