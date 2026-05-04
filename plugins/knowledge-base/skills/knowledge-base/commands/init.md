# Init Command

Initialize a folder as a Knowledge Base vault. Creates the `.archdesigner/` config directory, CLAUDE.md, MEMORY.md with memory files, optional starter documents, and installs graphify hooks for structural intelligence.

## Usage

```
/knowledge-base init                    # Initialize current working directory
/knowledge-base init ./my-project       # Relative path from cwd
/knowledge-base init ~/vaults/work      # Absolute path with tilde expansion
/knowledge-base init /tmp/demo-vault    # Absolute path
```

## What a Knowledge Base Vault Contains

```
<vault-root>/
├── .archdesigner/
│   ├── config.json          # Vault metadata (version, name, created, lastOpened)
│   └── _links.json          # Wiki-link backlink index (auto-maintained)
├── CLAUDE.md                # AI assistant instructions for this vault
├── MEMORY.md                # Curated memory index (preferences, conventions)
├── memory/
│   ├── archetype-preferences.md   # Diagram style preferences
│   └── topic-registry.md         # Known topics and their relationships
├── .graphifyignore          # Patterns excluded from graphify indexing
├── *.json                   # Architecture diagrams
├── *.md                     # Markdown documents
└── docs/                    # Optional: organized documentation
    ├── architecture/        # Architecture decision records
    ├── components/          # Component documentation
    └── guides/              # How-to guides
```

## Initialization Steps

Execute all 10 steps in order. Do not skip steps. Ask the user for input where indicated.

---

### Step 1: Resolve target directory

Parse the arguments passed from the SKILL.md dispatcher to determine the target path.

1. **No argument provided:** Use the current working directory (`$PWD`)
2. **Relative path provided** (e.g., `./my-project`, `../other`, `subdir`): Resolve relative to `$PWD`
3. **Absolute path provided** (e.g., `/tmp/vault`, `~/vaults/work`): Use as-is (expand `~`)

Resolve the path to an absolute canonical path:
```bash
TARGET_DIR=$(cd "<provided-path>" 2>/dev/null && pwd || echo "<provided-path>")
```

If the target directory does not exist, create it (including intermediate directories):
```bash
mkdir -p "<resolved-path>"
```

Confirm the resolved path with the user:
> Initializing vault at: `<resolved-absolute-path>`

**Check if it's already a vault:**
```bash
ls -la <resolved-path>/.archdesigner/config.json 2>/dev/null
```

If `config.json` exists, inform the user: "This directory is already a Knowledge Base vault." Ask if they want to reinitialize. If they decline, stop. If they accept, follow the **Reinitialize Rules** at the bottom of this file for all subsequent steps.

---

### Step 2: Ask vault name

Ask the user what to name the vault. Suggest the directory basename as the default:

```
What would you like to name this vault? (default: "<directory-basename>")
```

Store the answer as `VAULT_NAME`.

---

### Step 3: Create `.archdesigner/` config

Create the config directory and both config files inside the resolved path.

```bash
mkdir -p "<resolved-path>/.archdesigner"
```

**Write `<resolved-path>/.archdesigner/config.json`:**

```json
{
  "version": "1.0",
  "name": "<VAULT_NAME>",
  "created": "<ISO-8601-timestamp>",
  "lastOpened": "<ISO-8601-timestamp>"
}
```

- `version`: Always `"1.0"` for new vaults.
- `name`: The vault name from Step 2.
- `created` and `lastOpened`: Current timestamp in ISO 8601 format (e.g., `"2026-04-12T15:30:00Z"`).

**Write `<resolved-path>/.archdesigner/_links.json`:**

```json
{
  "updatedAt": "<ISO-8601-timestamp>",
  "documents": {},
  "backlinks": {}
}
```

Use the Write tool with full absolute paths for both files.

---

### Step 4: Ask about starter structure

Ask the user which optional starter content to create. Present three options:

```
Which starter structure would you like?

A) Minimal (recommended) — Just the config, CLAUDE.md, and memory files. Add documents as needed.

B) Documentation structure — Creates docs/ subdirectories (architecture/, components/, guides/) and a README.md.

C) Full starter kit — Everything in B, plus an ADR template and a getting-started guide with wiki-link examples.
```

Store the answer as `STARTER_CHOICE` (A, B, or C).

**If B or C, create directories:**
```bash
mkdir -p "<resolved-path>/docs/architecture"
mkdir -p "<resolved-path>/docs/components"
mkdir -p "<resolved-path>/docs/guides"
```

**If B or C, write `<resolved-path>/README.md`:**

```markdown
# <VAULT_NAME>

This is a Knowledge Base vault.

## Quick Start

- Create `.md` files anywhere in this directory
- Link documents using `[[wiki-links]]`
- Create `.json` diagram files using `/knowledge-base diagram <topic>`
- Use `/knowledge-base document <topic>` to generate structured documents

## Structure

- **Diagrams** (`.json`) — Architecture diagrams viewable in the visual editor
- **Documents** (`.md`) — Markdown documents with wiki-link cross-references
- **`.archdesigner/`** — Vault configuration (do not edit manually)
- **`memory/`** — Curated preferences and conventions for AI assistants

## Intelligence

This vault supports compound intelligence:
- `/graphify query "<question>"` — Search the structural knowledge graph
- `/mem-search "<query>"` — Search past session history
- `MEMORY.md` — Curated preferences and conventions
```

**If C, also write `<resolved-path>/docs/architecture/001-initial-architecture.md`:**

```markdown
# ADR-001: Initial Architecture

**Status:** Accepted
**Date:** <today's date as YYYY-MM-DD>

## Context

Describe the architectural context and problem.

## Decision

Describe the decision made.

## Consequences

What are the positive and negative consequences?

## Related

- [[README]]
```

**If C, also write `<resolved-path>/docs/guides/getting-started.md`:**

```markdown
# Getting Started

## Creating Documents

Create `.md` files anywhere in the vault. Use wiki-links to cross-reference:
- `[[document-name]]` — link to a document in the same folder
- `[[folder/document]]` — relative path from vault root
- `[[document#section]]` — link to a specific heading

## Creating Diagrams

Use the `/knowledge-base diagram` command:
```
/knowledge-base diagram "System authentication flow"
/knowledge-base diagram "Data pipeline architecture"
```

## Creating Documents and Diagrams Together

Use the `/knowledge-base create` command to generate both a document and a linked diagram:
```
/knowledge-base create "Microservices architecture"
```

## Linking Documents to Diagram Elements

Documents can be attached to diagram elements as cross-references. The backlink index in `.archdesigner/_links.json` tracks all connections automatically.

## Related

- [[README]]
- [[docs/architecture/001-initial-architecture]]
```

---

### Step 5: Write `CLAUDE.md`

Write `<resolved-path>/CLAUDE.md`. This file gives AI assistants context about the vault. Keep it lean and static.

```markdown
# <VAULT_NAME>

Knowledge Base vault.

## STRICT REQUIREMENT: Use the Knowledge Base Skill

**Every document and diagram operation in this vault — creation, generation, editing, writing — MUST go through the `/knowledge-base` skill. No exceptions, no shortcuts.**

This rule covers:
- Creating or generating new documents → `/knowledge-base document <topic>` or `/knowledge-base create <topic>`
- Creating or generating new diagrams → `/knowledge-base diagram <topic>` or `/knowledge-base create <topic>`
- Editing existing documents or diagrams → `/knowledge-base edit <path>`
- Any subagent dispatched to produce vault content

**Why this is non-negotiable:** The skill runs compound intelligence (graphify + claude-mem + MEMORY.md) before generating, enforces consistent formatting, applies the correct archetype, updates the topic registry, and writes flow explanation docs. Bypassing it — even by reading the skill files and replicating the rules manually — skips these steps and produces inconsistent, under-linked output.

**For subagents:** Any agent tasked with creating or editing content in this vault must invoke `Skill("knowledge-base", "<sub-command> <topic>")` directly. The agent must NOT replicate skill rules from memory or from reading skill files. If a task requires generating multiple topics, dispatch one agent per topic and have each invoke the skill for its topic.

## File Conventions

- `.json` files are architecture diagrams (visual editor format)
- `.md` files are documents with `[[wiki-link]]` cross-references
- `.archdesigner/` contains vault config and link index — do not edit manually
- `memory/` contains curated preferences — read before generating content

## Preferences and Conventions

See `MEMORY.md` for curated preferences, archetype choices, and topic conventions.
Check `memory/archetype-preferences.md` for diagram style preferences.
Check `memory/topic-registry.md` for known topics and their relationships.

## Intelligence

- `/graphify query "<question>"` — Search the structural knowledge graph for this vault
- `/mem-search "<query>"` — Search past session work and decisions
- See `MEMORY.md` for curated, durable preferences

## Archetypes

Diagram generation uses archetype files from `~/.claude/skills/knowledge-base/archetypes/`.
Each archetype defines layer conventions, icon mappings, connection semantics, and layout rules.
The `software-architecture` archetype is the default for system diagrams.

## graphify

This vault has a graphify knowledge graph at graphify-out/.

Rules:

- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- **After creating or editing any document or diagram in this vault, run `graphify . --update` to keep the knowledge graph current.**
```

---

### Step 6: Write `MEMORY.md` and `memory/` files

Create the memory directory:
```bash
mkdir -p "<resolved-path>/memory"
```

**Write `<resolved-path>/MEMORY.md`:**

```markdown
# <VAULT_NAME> — Memory Index

Curated preferences, conventions, and references for this vault. AI assistants read this file before generating content.

## How This Works

- Entries below are short summaries linking to detailed files in `memory/`
- Add new preferences by creating a file in `memory/` and linking it here
- Type prefixes: `feedback` (preferences), `reference` (pointers), `project` (context)

## Entries

- [Archetype preferences](memory/archetype-preferences.md) — Diagram style and archetype choices
- [Topic registry](memory/topic-registry.md) — Known topics, relationships, and naming conventions
```

**Write `<resolved-path>/memory/archetype-preferences.md`:**

```markdown
---
type: feedback
created: <ISO-8601-timestamp>
description: Diagram archetype and style preferences for this vault
---

# Archetype Preferences

Record diagram style preferences here as they emerge. Examples:

- Preferred archetype for system diagrams: `software-architecture`
- Color overrides or custom layer conventions
- Icon preferences for domain-specific concepts
- Layout density preference (sparse / moderate / dense)
```

**Write `<resolved-path>/memory/topic-registry.md`:**

```markdown
---
type: reference
created: <ISO-8601-timestamp>
description: Registry of topics covered in this vault and their relationships
---

# Topic Registry

Track topics covered in this vault and how they relate. This helps avoid duplicating content and enables intelligent cross-referencing.

## Topics

<!-- Add entries as topics are created:
- **Topic Name** — Brief description. Documents: [[doc1]], [[doc2]]. Diagrams: file.json
-->
```

---

### Step 7: Install graphify hook

Attempt to install graphify's Claude Code hook inside the vault directory. This enables automatic graph rebuilds when files change.

```bash
cd "<resolved-path>" && graphify claude install 2>&1
```

**If the command succeeds:** Report that graphify hooks are installed.

**If the command fails** (graphify not installed, command not found, or any error): Skip this step and inform the user:
> graphify is not installed or not available. Skipping hook installation. You can install it later with `pip install graphify-ai` and then run `graphify claude install` inside the vault directory.

Do not fail the entire init if graphify is unavailable. This step is optional.

---

### Step 8: Create `.graphifyignore`

Write `<resolved-path>/.graphifyignore` to exclude internal directories from graphify indexing:

```
# Knowledge Base vault internals — not useful for the knowledge graph
.archdesigner/
memory/
```

---

### Step 9: Build initial graphify index

If graphify is available (Step 7 succeeded), offer to build an initial index:

```
Would you like to build the initial graphify knowledge graph now?
This analyzes all documents and diagrams to create a searchable knowledge graph
(even an empty vault benefits — it initializes the index for future rebuilds).
```

If the user accepts:
```bash
cd "<resolved-path>" && graphify . --update
```

If graphify is not available, skip this step silently.

---

### Step 10: Print summary

Print a summary of everything that was created:

```
Knowledge Base vault initialized: <VAULT_NAME>

  Location:    <resolved-path>
  Config:      <resolved-path>/.archdesigner/config.json
  Link index:  <resolved-path>/.archdesigner/_links.json
  Claude:      <resolved-path>/CLAUDE.md
  Memory:      <resolved-path>/MEMORY.md + memory/
  Starter:     <A: "Minimal" | B: "Documentation structure" | C: "Full starter kit">

Intelligence:
  graphify:    <"Installed" | "Not available — install with pip install graphify-ai">
  claude-mem:  Active (automatic session capture)
  MEMORY.md:   Ready (add preferences as you work)

Next steps:
  - Generate a diagram:   /knowledge-base diagram "<topic>"
  - Generate a document:  /knowledge-base document "<topic>"
  - Generate both:        /knowledge-base create "<topic>"
  - Search past work:     /mem-search "<query>"
  - Query knowledge graph: /graphify query "<question>"
```

---

## Reinitialize Rules

When reinitializing an existing vault (detected in Step 1), follow these rules throughout all steps:

1. **Preserve `_links.json`:** Do NOT overwrite `<resolved-path>/.archdesigner/_links.json`. This file contains accumulated backlink data that would be lost. Skip writing it in Step 3.
2. **Update `config.json`:** Overwrite with a new `lastOpened` timestamp but preserve the original `created` timestamp. Read the existing file first to extract `created`.
3. **Only create files that don't exist:** In Steps 4-6, before writing any file (README.md, CLAUDE.md, MEMORY.md, memory files, starter documents), check if it already exists. If it does, do NOT overwrite it.
4. **Warn before overwriting:** If the user explicitly asks to overwrite an existing file during reinit, warn them: "This will replace your existing `<filename>` with the default template. Any customizations will be lost. Proceed?" Only overwrite after confirmation.
5. **Re-run graphify install:** Steps 7-9 can be re-run safely — graphify hooks are idempotent, `.graphifyignore` can be overwritten (it's a generated file), and re-indexing is always safe.

## Vault Config Schema Reference

```typescript
interface VaultConfig {
  version: string;     // Schema version (currently "1.0")
  name: string;        // Human-readable vault name
  created: string;     // ISO 8601 timestamp — set once at creation
  lastOpened: string;  // ISO 8601 timestamp — updated on each open/reinit
}

interface LinkIndex {
  updatedAt: string;
  documents: Record<string, {
    outboundLinks: string[];
    sectionLinks: { targetPath: string; section: string }[];
  }>;
  backlinks: Record<string, {
    linkedFrom: { sourcePath: string; section?: string }[];
  }>;
}
```
