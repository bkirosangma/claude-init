#!/usr/bin/env python3
"""
Transform a knowledge-base .md or .json file into skill-format conformance.
Content is preserved; only format, syntax, and structural links are adjusted.

Usage:
  kb_transform.py <path-or-glob> [--dry-run] [--add-conventions]

What changes (default):
  .md  — <span data-wiki-link="X">Y</span>  →  [[X]]
  .md  — YAML frontmatter at file top stripped; title promoted to H1
  .json — delegates to kb_validate.py --fix

With --add-conventions (additive):
  .md  — adds missing "Visual overview: [[slug.json]]" after H1
  .md  — adds missing "## Related" section if body wiki-links exist

What never changes:
  Prose, section order, heading hierarchy, file location, node coordinates,
  flow definitions, or --- horizontal rules inside the document body.
"""

import argparse
import glob
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kb_utils import backup_file

SCRIPTS_DIR = Path(__file__).parent

# Matches: <span data-wiki-link="path/to/file.md" class="wiki-link">any text</span>
SPAN_RE = re.compile(
    r'<span\s+data-wiki-link="([^"]+)"[^>]*>.*?</span>',
    re.IGNORECASE | re.DOTALL,
)

# A frontmatter block is ONLY valid when it starts on the very first line of the file.
# Pattern: starts with ---, then key:value lines, then closing ---
FRONTMATTER_RE = re.compile(r'\A---\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)', re.DOTALL)


def _transform_md(path: str, dry_run: bool, add_conventions: bool) -> list[str]:
    """Apply all format transforms to a markdown file. Returns list of change descriptions."""
    original = Path(path).read_text(encoding='utf-8')
    text = original
    changes: list[str] = []

    # ── 1. Strip YAML frontmatter (only if it starts on line 1) ───────────────
    fm_match = FRONTMATTER_RE.match(text)
    if fm_match:
        fm_body = fm_match.group(1)
        title_match = re.search(r'^title:\s*(.+)$', fm_body, re.MULTILINE)
        rest = text[fm_match.end():].lstrip('\n')
        # If the remaining text has no H1 heading but frontmatter had a title, promote it
        if title_match and not re.match(r'#\s', rest):
            extracted = title_match.group(1).strip().strip('"\'')
            rest = f'# {extracted}\n\n{rest}'
        text = rest
        changes.append('stripped YAML frontmatter')

    # ── 2. Convert <span data-wiki-link="X"> → [[X]] ──────────────────────────
    spans = SPAN_RE.findall(text)
    if spans:
        text = SPAN_RE.sub(lambda m: f'[[{m.group(1)}]]', text)
        changes.append(f'converted {len(spans)} span wiki-link(s) to [[...]] syntax')

    # ── 3. Visual overview link (--add-conventions only) ──────────────────────
    if add_conventions:
        slug = Path(path).stem
        companion = Path(path).parent / f'{slug}.json'
        has_overview = bool(re.search(r'visual overview:', text, re.IGNORECASE))

        if not has_overview and companion.exists():
            h1 = re.search(r'^#\s.+$', text, re.MULTILINE)
            if h1:
                ins = f'\nVisual overview: [[{slug}.json]]\n'
                text = text[:h1.end()] + ins + text[h1.end():]
                changes.append(f'added Visual overview link → [[{slug}.json]]')
        elif not has_overview:
            changes.append(f'no Visual overview added (no companion {slug}.json found)')

    # ── 4. ## Related section (--add-conventions only) ────────────────────────
    if add_conventions:
        has_related = bool(re.search(r'^##\s+related\b', text, re.IGNORECASE | re.MULTILINE))
        if not has_related:
            # Collect all [[...]] links; exclude the Visual overview JSON link
            slug = Path(path).stem
            all_links = re.findall(r'\[\[([^\]]+)\]\]', text)
            body_links = [
                l.split('|')[0]  # strip display part: [[path|display]] → path
                for l in all_links
                if not l.split('|')[0].strip().endswith('.json')
            ]
            unique = list(dict.fromkeys(body_links))  # deduplicate, preserve order

            if unique:
                section = '\n## Related\n\n' + '\n'.join(f'- [[{l}]]' for l in unique) + '\n'
                text = text.rstrip('\n') + '\n' + section
                changes.append(f'added ## Related section ({len(unique)} link(s))')

    if not changes:
        return []

    if not dry_run:
        bak = backup_file(path, 'transform-backup')
        Path(path).write_text(text, encoding='utf-8')
        from kb_validate_doc import validate_document as _vd
        if _vd(path).errors:
            changes.append(f'⚠ backup kept at {Path(bak).name} (validation errors remain)')
        else:
            Path(bak).unlink(missing_ok=True)

    return changes


def _transform_json(path: str, dry_run: bool) -> None:
    """Delegate JSON files to kb_validate --fix."""
    cmd = [sys.executable, str(SCRIPTS_DIR / 'kb_validate.py'), path]
    if not dry_run:
        cmd.append('--fix')
    subprocess.run(cmd)


def main():
    ap = argparse.ArgumentParser(
        description='Transform knowledge-base files into skill-format conformance.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument('path', help='File path or glob (.md or .json)')
    ap.add_argument('--dry-run', action='store_true', help='Show changes without writing')
    ap.add_argument('--add-conventions', action='store_true',
                    help='Also add missing Visual overview link and ## Related section')
    args = ap.parse_args()

    paths = glob.glob(args.path, recursive=True)
    if not paths and os.path.exists(args.path):
        paths = [args.path]
    if not paths:
        print(f'No files found matching: {args.path}', file=sys.stderr)
        sys.exit(1)

    total = len(paths)
    changed = 0

    for p in paths:
        ext = Path(p).suffix.lower()

        print(f'transform {p}')

        if ext == '.json':
            print('  ℹ JSON file — running kb_validate --fix')
            _transform_json(p, args.dry_run)
            print()
            continue

        if ext != '.md':
            print('  ℹ skipped (not .md or .json)\n')
            continue

        try:
            chgs = _transform_md(p, args.dry_run, args.add_conventions)
        except OSError as e:
            print(f'  ✗ {e}\n')
            continue

        if not chgs:
            print('  ✓ already conformant — no changes needed')
        else:
            for c in chgs:
                glyph = 'ℹ' if c.startswith('no ') else '✓'
                print(f'  {glyph} {c}')
            if args.dry_run:
                print('  — dry run — no files written')
            else:
                changed += 1

        print()

    verb = 'would change' if args.dry_run else 'changed'
    print(f'transform complete: {total} file(s) processed, {changed} {verb}')


if __name__ == '__main__':
    main()
