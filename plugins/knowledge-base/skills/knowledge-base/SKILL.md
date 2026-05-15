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
version: 1.3.0
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

## Mandatory Graphify Pre-Check

**Every sub-command except `init` MUST run this pre-check before generating, mutating, or answering anything.** It exists to prevent redundant content, surface relevant existing work, and warn about cross-references a mutation might break.

Skipping it — even when the user's intent looks obvious — is a defect. The user's request frames *what* they want; the pre-check determines whether that work already exists or which existing work it needs to link to.

### When the pre-check is skipped

- `init` — there is no graphify index yet on a fresh folder. Exempt.
- No vault detected (`.archdesigner/config.json` not found within 3 parent levels) — emit a one-line notice: *"No vault detected; skipping graphify pre-check. Existing-content awareness is unavailable for this run."* Then proceed.
- Vault detected but no `graphify-out/` directory — emit: *"Vault has no graphify index. Run `/graphify .` inside `<vaultRoot>` to enable existing-content awareness."* Then proceed.

In every other case the pre-check runs.

### Pre-Check Protocol

Inputs: `topic` (the user's query / target / file), `vaultRoot`.

1. **Stale-graph guard.** If `graphify-out/` exists, check whether it is older than the newest `*.md` / `*.json` / `*.svg` / `*.alphatex` in the vault:

   ```bash
   newest=$(find "<vaultRoot>" \( -name '*.md' -o -name '*.json' -o -name '*.svg' -o -name '*.alphatex' \) \
              -not -path '*/graphify-out/*' -not -path '*/.archdesigner/*' \
              -newer "<vaultRoot>/graphify-out/GRAPH_REPORT.md" -print -quit 2>/dev/null)
   if [ -n "$newest" ]; then
     (cd "<vaultRoot>" && graphify . --update 2>/dev/null) || true
   fi
   ```

   The pre-check is allowed to lie if and only if the index is current. Stale indexes silently miss recently added content, which is exactly the failure mode this guard is here to prevent.

2. **Query.** Run `graphify query "<topic>"` from the vault root and collect the top results (paths + similarity / community membership). Read `graphify-out/GRAPH_REPORT.md` for god-node and community context relevant to the topic. If `graphify-out/wiki/index.md` exists, prefer it over raw graph reads.

3. **Classify each result.** Use the following rubric — when in doubt, err toward STRONG (asking the user to confirm a near-duplicate is cheap; silently generating one is expensive):

   - **STRONG** — high semantic overlap AND a matching archetype/folder. The result is, in practice, the same topic.
   - **ADJACENT** — related (shares cluster / community / referenced concepts) but distinct topic.
   - **NONE** — no meaningful overlap.

4. **Decide.**

   - **One or more STRONG matches** → stop. Do not generate. Surface the matches and ask the user:

     > Found existing content that looks like the same topic:
     > - `<path1>` — <one-line summary>
     > - `<path2>` — <one-line summary>
     >
     > How would you like to proceed?
     > 1. **Open** the existing content (I'll print it / display the path).
     > 2. **Edit** it via `/kb edit <path>`.
     > 3. **Generate a new variant anyway** (e.g. different angle, deeper dive).

     Wait for the user's choice. Do not auto-open. Do not auto-generate.

   - **ADJACENT matches only** → continue with the sub-command, and pass them into `gatheredContext.relatedPaths` so the sub-command can weave links into its output (Related section, cross-references, "See also" bullets, etc.).

   - **NONE** → continue with the sub-command. No cross-links needed.

### Question-answering mode (graphify-first, then narrate)

When the user's request is a *question* about the vault rather than a generation/mutation command (e.g. "what's in my vault about X?", "do we have a diagram for Y?"), the pre-check is still mandatory and the answer style is graphify-first then narrate:

1. Run steps 1-3 above to gather matches.
2. Present the **paths and summaries** verbatim from graphify as the authoritative list.
3. Narrate around them: synthesise, explain, point out gaps — but the underlying source-of-truth is the graphify output, not LLM recall.

Never answer a vault-content question purely from memory when graphify is available; the index is fresher than your guess.

## Companion Intelligence (best-effort, after graphify)

After the mandatory graphify pre-check, also gather context from these two systems. They cover what graphify can't (temporal decisions, user preferences). They are *not* gates — a missing claude-mem result or absent MEMORY.md does not block the sub-command.

### claude-mem (Temporal)

Search past session work for anything related to the topic:
- Use MCP tool `mcp__plugin_claude-mem_mcp-search__search` with `query: "<topic>"`.
- Collect: past decisions, architectural patterns, prior diagrams on similar topics, lessons learned.

### MEMORY.md (Curated)

If a vault is detected, check for `<vault-root>/.archdesigner/MEMORY.md`:
- Read it for user preferences, topic registry entries, style feedback, and conventions.
- Also check `~/.claude/projects/*/memory/MEMORY.md` for project-level preferences.

### Context Assembly

Combine gathered context into a structured block that the sub-command can reference:

```
## Gathered Context

### Existing Related Content (graphify)
- strongMatches: [paths that triggered the short-circuit, if any]
- adjacentMatches: [paths to cross-link]
- topClusters: [community / god-node context relevant to the topic]

### Past Session Work (claude-mem)
- [relevant observations]

### User Preferences (MEMORY.md)
- [preferences and conventions]
```

Omit any section that yielded no results rather than including an empty one. If no vault is detected, only the claude-mem section will be populated; graphify and MEMORY.md sections are skipped with the notices above.
