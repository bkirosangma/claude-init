---
name: knowledge-base
description: >
  Unified skill for managing knowledge-base vaults. Sub-commands: init (set up a vault),
  diagram (generate a diagram on any topic), document (generate a standalone document),
  create (generate both a document and diagram, linked together),
  svg (generate a music SVG visualization using kb_svg.py),
  guitar-tabs (generate a playable guitar tab on any song or riff as alphaTex),
  edit (modify an existing diagram JSON — enforces placement constraints),
  validate (check / auto-fix a diagram JSON against the app schema),
  transform (bring an existing .md or .json file into skill-format conformance without changing content).
  Trigger on: "knowledge-base", "kb", "create architecture", "design diagram",
  "architecture of X", "create document", "write about X", "init vault",
  "initialize vault", "set up vault", "create about X", "diagram of X",
  "validate diagram", "fix diagram json", "check diagram",
  "edit diagram", "update diagram", "add to diagram", "modify diagram",
  "guitar tab", "guitar tabs", "guitar tab of X", "tab for X", "alphatex",
  "tablature", "fingerpicking pattern for X", "riff for X",
  "transform file", "fix format", "bring into conformance", "normalize vault files",
  "svg", "music svg", "staff notation", "fretboard diagram", "circle of fifths",
  "raga clock", "maqam jins", "chord box", "gamelan cipher", "tala wheel".
argument-hint: <sub-command> [args] — sub-commands: init, diagram, document, create, svg, guitar-tabs, edit, validate, transform
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion, Agent, WebSearch, WebFetch]
version: 1.2.0
---

# Knowledge Base

Unified skill for managing knowledge-base vaults — structured collections of documents and diagrams on any topic. Each vault stores its content, cross-references, and metadata under a `.archdesigner/` config directory.

## Usage

```
/knowledge-base init [path]              — Initialize a new vault at path (default: cwd)
/knowledge-base diagram <topic>          — Generate a diagram on <topic>
/knowledge-base document <topic> [-i]    — Generate a standalone document on <topic>
/knowledge-base create <topic> [-i]      — Generate both a document and diagram, linked together
/knowledge-base svg <topic>              — Generate a music SVG visualization (staff, fretboard, etc.)
/knowledge-base guitar-tabs <topic> [-i] — Generate a playable guitar tab (.alphatex) on <topic>
/knowledge-base edit <path> [change]     — Edit an existing diagram (enforces all placement rules)
/knowledge-base validate <path> [--fix]  — Validate (and optionally auto-fix) a diagram JSON file
/knowledge-base transform <path> [--dry-run] [--add-conventions]  — Conform an existing file to skill format
```

Options:
- `-i`, `--interactive` — Enter interactive mode: ask clarifying questions before generating content (available for `document`, `create`, and `guitar-tabs`)
- `--fix` — After validation, write the corrected JSON back to disk (a timestamped backup of the original is kept). Without this flag `validate` is read-only. (Available for `validate`.)
- `--dry-run` — Show what would change without writing any file. (Available for `transform`.)
- `--add-conventions` — Also add missing structural elements like Visual overview links and Related sections. (Available for `transform`.)

Examples:
```
/knowledge-base init ~/vaults/distributed-systems
/knowledge-base diagram "Kubernetes pod lifecycle"
/knowledge-base document "Event sourcing patterns" -i
/knowledge-base create "Microservices authentication flow"
/kb create "GraphQL federation architecture" -i
/kb svg "Raga Yaman clock"
/kb svg "Jins Hijaz on D"
/kb svg "Dm7 chord box"
/kb guitar-tabs "Hotel California intro fingerpicking"
/knowledge-base guitar-tabs "G major pentatonic warm-up riff" -i
/knowledge-base validate ./auth-flow.json
/kb validate ./broken-diagram.json --fix
/knowledge-base transform ./react-next/nextjs-configuration/nextjs-configuration.md
/kb transform "react-next/**/*.md" --dry-run
/kb transform ./old-diagram.json --add-conventions
```

## Sub-Command Routing

Parse the user's argument string to determine the sub-command, then dispatch to the corresponding command file.

### Parsing Rules

1. Split the argument string on whitespace. The first token is the sub-command candidate.
2. Everything after the sub-command token is the **remaining args** (topic, path, flags).
3. Check for the `-i` or `--interactive` flag anywhere in remaining args — if present, strip it and set `interactive = true`.

### Dispatch Table

| First token         | Action                                                                                             |
|---------------------|----------------------------------------------------------------------------------------------------|
| *(empty)* or `help` | Print the Usage block above with short descriptions of each sub-command. Do not read any file.     |
| `init`              | Read `~/.claude/skills/knowledge-base/commands/init.md` and execute it. Pass remaining args as **path** (default to cwd if empty). |
| `diagram`           | Read `~/.claude/skills/knowledge-base/commands/diagram.md` and execute it. Pass remaining args as **topic**. |
| `document`          | Read `~/.claude/skills/knowledge-base/commands/document.md` and execute it. Pass remaining args as **topic**. Pass `interactive` flag. |
| `create`            | Read `~/.claude/skills/knowledge-base/commands/create.md` and execute it. Pass remaining args as **topic**. Pass `interactive` flag. |
| `svg`               | Read `~/.claude/skills/knowledge-base/commands/svg.md` and execute it. Pass remaining args as **topic**. |
| `guitar-tabs`       | Read `~/.claude/skills/knowledge-base/commands/guitar-tabs.md` and execute it. Pass remaining args as **topic** (song / riff / pattern name). Pass `interactive` flag. Output is an `.alphatex` file. Aliases recognised at parse time: `guitar-tab`, `tabs`, `tab`. |
| `edit`              | Read `~/.claude/skills/knowledge-base/commands/edit.md` and execute it. Pass remaining args as **path** (the diagram file) followed by an optional description of the change. |
| `validate`          | Read `~/.claude/skills/knowledge-base/commands/validate.md` and execute it. Pass remaining args as **path** (a file or glob). Pass a `fix` flag when `--fix` appears in the args (strip the flag before passing the path). |
| `transform`         | Read `~/.claude/skills/knowledge-base/commands/transform.md` and execute it. Pass remaining args as **path** (a file or glob). Pass `dryRun = true` when `--dry-run` appears; pass `addConventions = true` when `--add-conventions` appears. Strip both flags before passing the path. |
| *anything else*     | Treat the **entire** argument string (including the unrecognized token) as the **topic**. Route to `create` — this is the most common use case. Read `~/.claude/skills/knowledge-base/commands/create.md`. |

When reading a command file, follow every instruction inside it. The command file is the authority on how to execute that sub-command.

## Vault Detection

Before dispatching any sub-command, determine whether we are inside a vault.

### Detection Algorithm

1. Start at the current working directory.
2. Check if `.archdesigner/config.json` exists in this directory.
3. If not found, move one level up. Repeat up to **3 parent levels** (4 directories total including cwd).
4. If found:
   - That directory is the **vault root**.
   - Read `.archdesigner/config.json` to get `vaultName` and other vault settings.
   - Pass vault root path and config to the sub-command.
5. If not found after checking all levels:
   - Warn the user: "No vault detected in the current directory tree. Vault-specific features (cross-referencing, topic registry, backlinks) will not be available. Run `/knowledge-base init` to set up a vault."
   - Still proceed with the sub-command — documents and diagrams can be generated without a vault, they just won't be registered.

### Exception

The `init` sub-command does NOT require an existing vault (it creates one). Skip the "not found" warning for `init`.

## Compound Intelligence

Before executing any sub-command (after vault detection, before reading the command file), gather context from all available intelligence systems. This context is passed to the sub-command so it can produce higher-quality, non-redundant output.

### 1. graphify (Structural)

If a vault is detected and `graphify-out/` exists inside the vault root:
- Query the vault's knowledge graph for content related to the topic: `/graphify query "<topic>"`
- Read `graphify-out/GRAPH_REPORT.md` for god nodes and community structure relevant to the topic.
- Collect: related existing documents, diagrams, cross-references, and structural clusters.

### 2. claude-mem (Temporal)

Search past session work for anything related to the topic:
- Use MCP tool `mcp__plugin_claude-mem_mcp-search__search` with `query: "<topic>"`.
- Collect: past decisions, architectural patterns, prior diagrams on similar topics, lessons learned.

### 3. MEMORY.md (Curated)

If a vault is detected, check for `<vault-root>/.archdesigner/MEMORY.md`:
- Read it for user preferences, topic registry entries, style feedback, and conventions.
- Also check `~/.claude/projects/*/memory/MEMORY.md` for project-level preferences.

### Context Assembly

Combine gathered context into a structured block that the sub-command can reference:

```
## Gathered Context

### Existing Related Content
- [list of related docs/diagrams found via graphify]

### Past Session Work
- [relevant observations from claude-mem]

### User Preferences
- [preferences and conventions from MEMORY.md]
```

If a particular intelligence system yields no results, omit its section rather than including an empty one. If no vault is detected, only claude-mem context will be available.
