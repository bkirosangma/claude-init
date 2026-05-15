# Command: transform

Transform an existing file to conform to knowledge-base skill conventions. Content is preserved — only syntax, formatting, and structural links are adjusted. Delegates all logic to `kb_transform.py`.

## Usage

```
/knowledge-base transform <path> [--dry-run] [--add-conventions]
/knowledge-base transform "<glob>"
```

- `<path>` — file path or glob (`.md` or `.json`, or e.g. `react-next/**/*.md`)
- `--dry-run` — show what would change without writing any file
- `--add-conventions` — also add missing structural elements (Visual overview link, Related section)

## What changes / what doesn't

| Default | With `--add-conventions` |
|---------|--------------------------|
| `<span data-wiki-link="X">Y</span>` → `[[X]]` | + Missing `Visual overview: [[slug.json]]` added after H1 |
| YAML frontmatter `title:` promoted to H1 (when missing) | + Missing `## Related` section added if body wiki-links exist |
| YAML frontmatter `sources:` rewritten to canonical block-list (inline `sources: [{...}]` form is silently dropped by the project parser; we rewrite). | |
| Frontmatter is preserved when (and only when) it carries a non-empty `sources:` field; legacy `title:`-only blocks are stripped. | |
| `.json` files: full validate `--fix` pass | |

Never changed: prose, section order, heading hierarchy, file location, node coordinates, flow definitions, `---` horizontal rules in body.

## Step 0: Mandatory Graphify Pre-Check (Awareness)

Before running the transform script, run the **Mandatory Graphify Pre-Check** defined in `SKILL.md`. Use the **target path(s) — and their parent collection** as the topic; transforms reshape structure, so adjacent files in the same collection are the relevant context.

This is an **awareness step**, not a gate. The user has explicitly asked to transform the file(s); a STRONG match doesn't short-circuit. Instead:

- **STRONG match** for any target path (a sibling already conforms to the format you're transforming toward) → surface it once as a reference exemplar:

  > Reference: `<sibling-path>` already follows the conformant format. The transform will bring `<target>` to the same shape.

- **ADJACENT matches** within the collection → surface "these N siblings may also need transforming" so the user can decide whether to expand the glob. Do not auto-expand; respect the user's path argument.

- **NONE** → continue silently.

The pre-check is skipped only when no vault is detected or no graphify index exists (SKILL.md emits the standard notice). When `--dry-run` is set the pre-check still runs — its output frames the dry-run report.

## Step 1: Run the transform script

```bash
python3 ~/.claude/skills/knowledge-base/scripts/kb_transform.py "<path>" [--dry-run] [--add-conventions]
```

The script handles all transforms:

- `.md` files: rewrites/strips frontmatter (sources-aware), converts span wiki-links, optionally adds conventions
- `.json` files: delegates to `kb_validate.py --fix`
- Creates a `.transform-backup-<ISO>` before writing any file
- Prints a per-file report with change summaries and a final total

## Step 2: Present the output

Print the script's stdout directly to the user. Do not reformat it.

## Step 3: Vault integration (if files were changed and not --dry-run)

If a vault is detected and files were written:

```bash
cd "<vault-root>" && graphify . --update 2>/dev/null || true
```

Skip silently on failure.

### Idempotence on optional fields

`/kb transform` does NOT auto-populate any of:
- `flows[].nodeOrders`, `flows[].startNodeIds`, `flows[].endNodeIds`
- top-level `sources`, per-entity `sources`
- `attachedTo`

These are author-discretion fields. Re-running `transform` against an already-transformed file leaves them untouched.

`--add-conventions` in interactive mode (`-i`) MAY prompt the user to add `sources` if the file lacks them; it never adds without user consent.
