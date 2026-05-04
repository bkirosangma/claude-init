#!/usr/bin/env python3
"""
Migrate loose flow-*.md files into a flow-descriptions/ subfolder inside each topic.

A "topic folder" is any directory containing a <name>/<name>.md + <name>/<name>.json pair.
Flow files are any flow-*.md files found directly in the topic root (not already inside
a flow-descriptions/ subfolder).

What this script does per topic folder:
  1. Moves flow-*.md files → flow-descriptions/<flow-id>.md
  2. Updates DocumentMeta filenames in the topic's .json diagram
  3. Updates [[flow-id.md]] wiki-links in .md files inside the topic folder

Usage:
  kb_migrate_flows.py <vault-root-or-dir> [--dry-run]

Exit codes: 0 = success (or nothing to do), 1 = errors
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kb_utils import backup_file


def _find_topic_folders(root: Path) -> list[Path]:
    """Return all topic folders under root (directories where <name>/<name>.md exists)."""
    topics = []
    for d in sorted(root.rglob('*')):
        if not d.is_dir():
            continue
        name = d.name
        if name.startswith('.'):
            continue
        # Skip flow-descriptions folders and .archdesigner
        if name in ('flow-descriptions', '.archdesigner', 'memory', 'graphify-out', '.claude'):
            continue
        slug_md = d / f'{name}.md'
        slug_json = d / f'{name}.json'
        if slug_md.exists() or slug_json.exists():
            topics.append(d)
    return topics


def _migrate_topic(topic_dir: Path, dry_run: bool) -> list[str]:
    """Migrate one topic folder. Returns list of change descriptions."""
    changes: list[str] = []
    name = topic_dir.name

    # Find loose flow-*.md files (skip files already inside flow-descriptions/)
    flow_files = [
        f for f in topic_dir.glob('flow-*.md')
        if f.parent == topic_dir  # must be directly in topic root
    ]
    if not flow_files:
        return []

    flow_dir = topic_dir / 'flow-descriptions'

    if not dry_run:
        flow_dir.mkdir(exist_ok=True)

    for ff in sorted(flow_files):
        dest = flow_dir / ff.name
        if dry_run:
            changes.append(f'move {ff.relative_to(topic_dir.parent)} → {dest.relative_to(topic_dir.parent)}')
        else:
            shutil.move(str(ff), str(dest))
            changes.append(f'moved {ff.name} → flow-descriptions/{ff.name}')

    # ── Update DocumentMeta filenames in the diagram JSON ──────────────────────
    json_path = topic_dir / f'{name}.json'
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as e:
            changes.append(f'⚠ could not read {json_path.name}: {e}')
            data = None

        if data is not None and isinstance(data.get('documents'), list):
            updated = False
            flow_names = {ff.name for ff in flow_files}
            for doc in data['documents']:
                fn = doc.get('filename', '')
                # Match: <slug>/<flow-id>.md  (not already containing flow-descriptions)
                fn_path = Path(fn)
                if (fn_path.suffix == '.md'
                        and fn_path.name.startswith('flow-')
                        and fn_path.name in flow_names
                        and 'flow-descriptions' not in fn_path.parts):
                    new_fn = str(Path(fn_path.parent) / 'flow-descriptions' / fn_path.name)
                    changes.append(f'JSON: {fn!r} → {new_fn!r}')
                    doc['filename'] = new_fn
                    updated = True

            if updated and not dry_run:
                bak = backup_file(str(json_path), 'migrate-backup')
                json_path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
                Path(bak).unlink(missing_ok=True)

    # ── Update [[flow-id.md]] wiki-links in all .md files in the topic folder ──
    flow_names_set = {ff.name for ff in flow_files}
    # Pattern: [[flow-something.md]] or [[flow-something.md|Display]]
    WIKI_RE = re.compile(r'\[\[(' + '|'.join(re.escape(n) for n in flow_names_set) + r')(\|[^\]]+)?\]\]')

    for md_file in topic_dir.glob('*.md'):
        if md_file.parent != topic_dir:
            continue
        try:
            text = md_file.read_text(encoding='utf-8')
        except OSError as e:
            changes.append(f'⚠ could not read {md_file.name}: {e}')
            continue

        new_text = WIKI_RE.sub(
            lambda m: f'[[flow-descriptions/{m.group(1)}{m.group(2) or ""}]]',
            text,
        )
        if new_text != text:
            changes.append(f'MD links updated in {md_file.name}')
            if not dry_run:
                bak = backup_file(str(md_file), 'migrate-backup')
                md_file.write_text(new_text, encoding='utf-8')
                Path(bak).unlink(missing_ok=True)

    return changes


def main():
    ap = argparse.ArgumentParser(
        description='Migrate loose flow-*.md files into flow-descriptions/ subfolders.',
    )
    ap.add_argument('root', help='Vault root or directory to scan')
    ap.add_argument('--dry-run', action='store_true', help='Report changes without writing')
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f'Error: {root} is not a directory', file=sys.stderr)
        sys.exit(1)

    topics = _find_topic_folders(root)
    if not topics:
        print(f'No topic folders found under {root}')
        sys.exit(0)

    total = len(topics)
    changed = 0
    errors = 0

    for topic_dir in topics:
        label = str(topic_dir.relative_to(root))
        try:
            chgs = _migrate_topic(topic_dir, args.dry_run)
        except Exception as e:
            print(f'✗ {label}: {e}')
            errors += 1
            continue

        if chgs:
            print(f'migrate {label}')
            for c in chgs:
                glyph = '⚠' if c.startswith('⚠') else ('ℹ' if args.dry_run else '✓')
                print(f'  {glyph} {c}')
            if args.dry_run:
                print('  — dry run — no files written')
            changed += 1
            print()

    verb = 'would change' if args.dry_run else 'changed'
    status = f'migrate complete: {total} topic(s) scanned, {changed} {verb}'
    if errors:
        status += f', {errors} error(s)'
    print(status)
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
