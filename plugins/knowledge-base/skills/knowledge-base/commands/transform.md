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
| YAML frontmatter stripped; title promoted to H1 | + Missing `## Related` section added if body wiki-links exist |
| `.json` files: full validate `--fix` pass | |

Never changed: prose, section order, heading hierarchy, file location, node coordinates, flow definitions, `---` horizontal rules in body.

## Step 1: Run the transform script

```bash
python3 ~/.claude/skills/knowledge-base/scripts/kb_transform.py "<path>" [--dry-run] [--add-conventions]
```

The script handles all transforms:

- `.md` files: strips frontmatter, converts span wiki-links, optionally adds conventions
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
