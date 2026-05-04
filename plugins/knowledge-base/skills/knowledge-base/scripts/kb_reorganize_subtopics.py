#!/usr/bin/env python3
"""
Move topic folders from a flat collection into a parent topic's subtopics directory.

Usage:
  kb_reorganize_subtopics.py <collection-dir> <parent-slug> [--dry-run]

Example:
  kb_reorganize_subtopics.py react-next nextjs-and-reactjs

This moves every topic folder in <collection-dir> EXCEPT <parent-slug> itself
into <collection-dir>/<parent-slug>/. It then updates wiki-links in all .md
files and DocumentMeta filenames in all .json files.

Wiki-link rewrite:
  [[<collection>/<slug>/...]]  →  [[<collection>/<parent-slug>/<slug>/...]]
  [[<slug>/...]]               →  same (relative, still resolves)

DocumentMeta rewrite:
  "<collection>/<slug>/..."    →  "<collection>/<parent-slug>/<slug>/..."

Exit codes: 0 = success, 1 = errors
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kb_utils import backup_file


def _is_topic_folder(d: Path) -> bool:
    name = d.name
    return (d / f'{name}.md').exists() or (d / f'{name}.json').exists()


def main():
    ap = argparse.ArgumentParser(description='Move sibling topics into a parent topic subfolder.')
    ap.add_argument('collection', help='Collection directory (e.g. react-next)')
    ap.add_argument('parent_slug', help='Parent topic slug that becomes the root (e.g. nextjs-and-reactjs)')
    ap.add_argument('--dry-run', action='store_true', help='Show changes without writing')
    args = ap.parse_args()

    collection = Path(args.collection).resolve()
    parent_slug = args.parent_slug
    parent_dir = collection / parent_slug

    if not parent_dir.is_dir():
        print(f'Error: parent topic folder not found: {parent_dir}', file=sys.stderr)
        sys.exit(1)

    # Find all sibling topic folders (exclude the parent itself)
    siblings = sorted([
        d for d in collection.iterdir()
        if d.is_dir()
        and d.name != parent_slug
        and not d.name.startswith('.')
        and _is_topic_folder(d)
    ])

    if not siblings:
        print('No sibling topic folders found to move.')
        sys.exit(0)

    print(f'Moving {len(siblings)} topic(s) into {collection.name}/{parent_slug}/')
    print()

    # ── Step 1: Move folders ────────────────────────────────────────────────────
    moved: list[tuple[str, str]] = []  # (old_slug, new_slug) for link rewriting
    for sib in siblings:
        slug = sib.name
        dest = parent_dir / slug
        if dry_run := args.dry_run:
            print(f'  ℹ would move {collection.name}/{slug}/ → {collection.name}/{parent_slug}/{slug}/')
        else:
            if dest.exists():
                print(f'  ⚠ destination already exists, skipping: {dest}')
                continue
            shutil.move(str(sib), str(dest))
            print(f'  ✓ moved {collection.name}/{slug}/ → {collection.name}/{parent_slug}/{slug}/')
        moved.append(slug)

    print()

    # Build the collection name for link rewriting
    collection_name = collection.name

    # ── Step 2: Update wiki-links in all .md files ─────────────────────────────
    # Pattern: [[collection_name/<slug>/...]] → [[collection_name/parent_slug/<slug>/...]]
    # We must rewrite for each moved slug to avoid false positives.
    WIKI_RE = re.compile(r'\[\[(' + re.escape(collection_name) + r'/(' + '|'.join(re.escape(s) for s in moved) + r')(/[^\]]*)?)\]\]')

    def _rewrite_link(m: re.Match) -> str:
        full_path = m.group(1)
        slug = m.group(2)
        rest = m.group(3) or ''
        new_path = f'{collection_name}/{parent_slug}/{slug}{rest}'
        return f'[[{new_path}]]'

    # Scan all .md files in the entire vault (parent of collection)
    vault_root = collection.parent
    md_files = list(vault_root.rglob('*.md'))
    changed_md = 0

    for md_path in sorted(md_files):
        # Skip backup files and memory files
        if any(m in md_path.name for m in ('.transform-backup-', '.invalid-backup-', '.migrate-backup-')):
            continue
        try:
            text = md_path.read_text(encoding='utf-8')
        except OSError:
            continue

        new_text = WIKI_RE.sub(_rewrite_link, text)
        if new_text != text:
            changes = []
            for m in WIKI_RE.finditer(text):
                old = f'[[{m.group(1)}]]'
                new = _rewrite_link(m)
                changes.append(f'{old} → {new}')

            rel = md_path.relative_to(vault_root)
            print(f'  MD {rel}')
            for c in changes:
                print(f'    {c}')

            if not args.dry_run:
                bak = backup_file(str(md_path), 'reorg-backup')
                md_path.write_text(new_text, encoding='utf-8')
                Path(bak).unlink(missing_ok=True)
            changed_md += 1

    # ── Step 3: Update DocumentMeta filenames in .json files ───────────────────
    # Pattern: "<collection_name>/<slug>/..." → "<collection_name>/<parent_slug>/<slug>/..."
    changed_json = 0
    json_files = list(vault_root.rglob('*.json'))
    BACKUP_MARKERS = ('.transform-backup-', '.invalid-backup-', '.migrate-backup-', '.history.json')

    for jp in sorted(json_files):
        if any(m in jp.name for m in BACKUP_MARKERS):
            continue
        try:
            data = json.loads(jp.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            continue

        docs = data.get('documents', [])
        if not docs:
            continue

        updated = False
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            fn = doc.get('filename', '')
            # Match: <collection_name>/<slug>/...  where slug is one of the moved ones
            for slug in moved:
                prefix = f'{collection_name}/{slug}/'
                if fn.startswith(prefix):
                    doc['filename'] = f'{collection_name}/{parent_slug}/{slug}/' + fn[len(prefix):]
                    updated = True
                    break

        if updated:
            rel = jp.relative_to(vault_root)
            print(f'  JSON {rel}: updated DocumentMeta filenames')
            if not args.dry_run:
                bak = backup_file(str(jp), 'reorg-backup')
                jp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
                Path(bak).unlink(missing_ok=True)
            changed_json += 1

    print()
    verb = 'would update' if args.dry_run else 'updated'
    print(f'reorganize complete: {len(moved)} topic(s) moved, {changed_md} .md {verb}, {changed_json} .json {verb}')


if __name__ == '__main__':
    main()
