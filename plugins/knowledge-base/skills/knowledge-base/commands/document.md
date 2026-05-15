# Command: document

Generate a standalone markdown document on any topic. Produces comprehensive, well-structured prose -- not a template or outline.

## Usage

```
/knowledge-base document <topic>           # Generate directly using compound intelligence context
/knowledge-base document <topic> -i        # Interactive mode: ask clarifying questions first
/knowledge-base document <topic> --interactive
```

## Inputs

The dispatcher passes:
- **topic** — everything after the `document` token, with `-i`/`--interactive` stripped
- **interactive** — boolean flag (`true` if `-i` or `--interactive` was present)
- **vaultRoot** — absolute path to detected vault root (or `null` if no vault)
- **vaultConfig** — parsed `.archdesigner/config.json` (or `null`)
- **gatheredContext** — compound intelligence context block assembled by SKILL.md

## Step 0: Mandatory Graphify Pre-Check

Before parsing arguments, before structural planning, before any LLM generation, run the **Mandatory Graphify Pre-Check** defined in `SKILL.md` against `<topic>`. SKILL.md owns the protocol; do not re-implement it here.

Outcomes:
- **STRONG match found** → stop. Surface the matching paths to the user via the SKILL.md dialog ("Open / Edit / Generate-new-anyway?") and wait for their choice. Do not generate a duplicate document.
- **ADJACENT matches** → continue. Carry the matched paths in `gatheredContext.adjacentMatches` and weave them into the document's "Related" section in Step 5.
- **NONE** → continue.

The pre-check is skipped only when no vault is detected or no graphify index exists (SKILL.md emits the standard notice in either case).

## Step 1: Parse Arguments

1. The **topic** string is the subject of the document. It may be multiple words (e.g., `"Event sourcing patterns"`).
2. If the topic is empty, ask the user: "What topic should the document cover?"
3. Derive a **topic-slug** via script — do not compute manually:

```bash
SLUG=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_utils.py slug "<topic>")
# If vault detected, check for duplicates:
SLUG=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_utils.py next-slug "$SLUG" "<vault-root>/memory/topic-registry.md")
```

## Step 1b: Suggest Placement

If `vaultRoot` is set, determine which collection (folder) this new document belongs in before generating content.

1. **Run the placement script**:

```bash
PLACEMENT=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_suggest_placement.py \
  --topic "<topic-slug>" \
  --vault-root "<vaultRoot>")
```

2. **Merge with graphify context**: From `gatheredContext`, identify the collection paths of the most semantically related existing topics (if graphify results are available).

3. **Present to the user** — combine the script's structural suggestion with any graphify semantic signal, then ask:

> **Where should this document be placed?**
>
> Offer up to 4 options drawn from the script's `suggestions[]`, using their `display` and `reason` fields. Always include a "Vault root" option and an "Other (type path)" option.

4. **Apply the confirmed path**: Set `topicFolder = "<vaultRoot>/<confirmed-path>/<topic-slug>/"` (create with `mkdir -p`). Write the document to `<topicFolder>/<topic-slug>.md`.

5. **If no vault detected**: skip this step and use `<cwd>/<topic-slug>/` as the topic folder.

## Step 1c: Select Document Template via Archetype

Run the archetype selection script to choose a template based on the topic and purpose:

```bash
ARCHETYPE_RESULT=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_archetype.py \
  --archetypes-dir ~/.claude/skills/knowledge-base/archetypes \
  --topic "<topic>" \
  --output-type document \
  --purpose-hint "<topic>")
```

Parse the 3-token output: `<name> <subtype> <path>`.

- If output is `no-match`: skip this step. Generate the document using the existing free-form structure heuristics (Step 4 below).
- If `subtype` is one of: `theory-primer`, `biography`, `song-breakdown`, `instrument-profile`, `tradition-overview`, `history-timeline`, `comparative`, or `default`: read the template at `<path>` and follow its body section structure when generating the document.
- If `subtype` is `-` (single-file archetype): treat as no-match and skip.

When a template is selected, the document MUST include the shared frontmatter and closing sections defined in the template. The body sections follow the template's order. Substantive prose still applies — the template defines structure, not content.

## Step 1.5: Gather Sources

Sources are mandatory. Use WebSearch to find 2–4 canonical online resources for the topic. Prefer the topic's primary literature over derivative blog posts. Record as:

```yaml
sources:
  - url: https://...
    title: Optional display label
```

These go into the document's YAML frontmatter (top of file, between `---` delimiters).

## Step 2: Detect Vault and Gather Context

The SKILL.md dispatcher handles vault detection and compound intelligence gathering before this command runs. Use the passed-in `vaultRoot`, `vaultConfig`, and `gatheredContext`.

Additionally, perform these document-specific context lookups:

### 2a. Topic Registry

If `vaultRoot` is set, check for `<vaultRoot>/memory/topic-registry.md`:

```bash
cat "<vaultRoot>/memory/topic-registry.md" 2>/dev/null
```

If it exists, scan for entries related to the current topic. This helps avoid duplicate documents and enables cross-referencing with existing content.

### 2b. Graphify — Related Content

If `vaultRoot` is set and `gatheredContext` includes graphify results, extract:
- Existing **diagrams** (`.json` files) on related topics -- these can be wiki-linked
- Existing **documents** (`.md` files) on adjacent topics -- these can be cross-referenced
- Structural clusters that include the topic's domain

### 2c. Claude-mem — Past Work

From `gatheredContext`, extract:
- Past decisions or discoveries related to the topic
- User preferences for document structure, depth, or style
- Previous documents generated on similar topics (to avoid redundancy)

### 2d. Vault MEMORY.md

If `vaultRoot` is set, check for `<vaultRoot>/.archdesigner/MEMORY.md`:

```bash
cat "<vaultRoot>/.archdesigner/MEMORY.md" 2>/dev/null
```

Look for feedback entries about:
- Preferred document depth (overview vs. deep-dive)
- Style preferences (academic, practical, tutorial-style)
- Structural conventions (e.g., always include a "Trade-offs" section)

## Step 3: Interactive Mode (if `-i` flag set)

If `interactive` is `true`, ask the user 2-3 targeted questions before generating. Tailor the questions based on the topic and any context gathered. Good defaults:

1. **Target audience**: "Who is the target audience? (e.g., senior engineers, beginners, decision-makers)"
2. **Depth level**: "What depth level? (e.g., executive overview, working knowledge, deep-dive reference)"
3. **Specific angles**: "Any specific angles or subtopics to emphasize? (e.g., trade-offs, migration path, comparison with alternatives)"

Wait for the user's answers before proceeding to Step 4. Incorporate their answers into the document generation.

If `interactive` is `false`, skip this step entirely and generate directly using the topic plus all gathered context.

## Step 4: Generate the Document

Write a comprehensive, well-structured markdown document. This is the core output -- it must be substantive prose, not a skeleton or template.

### Document Structure

```markdown
---
sources:
  - url: https://...
    title: Optional display label
---

# <Topic Title>

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

- [[wiki-link-to-related-doc]]
- [[wiki-link-to-related-diagram.json]]
```

### Content Guidelines

1. **Title as H1** — use the topic as-is or a slightly refined version
2. **Sections with H2/H3 headings** — organize logically for the topic domain
3. **Prose-first** — write full paragraphs, not bullet-point outlines. Use lists only where they genuinely aid comprehension (e.g., listing concrete steps, enumerating options)
4. **Substantive** — each section should teach or explain something. Avoid filler sentences and vague generalizations
5. **Contextual depth** — if interactive mode provided a depth preference, honor it. Otherwise default to "working knowledge" level: enough for a practitioner to understand and apply
6. **Code examples** where relevant — use fenced code blocks with language hints
7. **Diagrams** — if a related diagram exists in the vault, reference it: `See [[diagram-name.json]] for a visual overview.`
8. **Cross-references** — if related documents exist in the vault, include `[[other-doc]]` wiki-links in the body text or in a "Related" section at the end
9. **YAML frontmatter for sources** — the document begins with a `---` frontmatter block carrying the `sources` list gathered in Step 1.5. Use **block-list syntax only** (each entry on its own line, prefixed with `- url:`); inline form (`sources: [{...}]`) is silently treated as an unknown key by the app's frontmatter parser. Other metadata is tracked in the topic registry, not in the file itself

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

Use the `topicFolder` confirmed in Step 1b. Write the document to `<topicFolder>/<topic-slug>.md` (create the folder with `mkdir -p` if it doesn't exist).

If no vault detected, write to `<cwd>/<topic-slug>/<topic-slug>.md`.

Before writing, check if a file with the same name already exists:

```bash
ls "<output-path>" 2>/dev/null
```

If it exists, ask the user: "A document named `<topic-slug>.md` already exists. Should I overwrite it, or use a different name?"

Write the document using the Write tool.

## Step 5: Update Vault State (if in vault)

If `vaultRoot` is set, perform these post-generation updates:

### 5a. Update Topic Registry

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
  --doc "<relative-path-from-vault-root>"
```

### 5b. Update Graphify

If graphify is available in the vault (check for `graphify-out/` or `.graphifyignore`), rebuild the index to include the new document:

```bash
cd "<vaultRoot>" && graphify . --update 2>/dev/null || true
```

If `graphify` is not on PATH, try the Python module:

```bash
cd "<vaultRoot>" && python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))" 2>/dev/null || true
```

If neither works, skip silently -- graphify update is best-effort.

### 5c. Note on Link Index

The `_links.json` wiki-link backlink index updates automatically when the vault is opened in Architecture Designer. No manual update is needed here.

## Report

After completing all steps, print a summary:

```
Document generated: <Topic>
  File: <absolute-path-to-document>
  Sections: <count> sections
  Wiki-links: <count> cross-references included
  Vault: <vault-name> (or "none — standalone document")
  Registry: <updated | created | skipped (no vault)>
```
